"""
Identificação de falantes (diarização): descobre QUEM fala QUANDO e junta isso ao
texto do Whisper, gerando falas como "Voz 1: ...", "Voz 2: ...".

Usa o sherpa-onnx, que roda localmente e sem conta em nenhum serviço:
    - segmentação: pyannote/segmentation-3.0 (MIT), convertido para ONNX;
    - impressão digital de voz: WeSpeaker ResNet34 treinado no VoxCeleb (Apache-2.0).
Os dois modelos somam ~33 MB e são baixados uma única vez (ou já vêm no executável).
"""

from __future__ import annotations

import bisect
import hashlib
import os
import sys
import tarfile
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import numpy as np

TAXA = 16000  # Hz; o Whisper e os dois modelos trabalham em 16 kHz mono

_GITHUB = "https://github.com/k2-fsa/sherpa-onnx/releases/download"
# (nome do arquivo, URL, sha256 do download, arquivo dentro do .tar.bz2 ou None)
MODELOS = {
    "segmentacao": (
        "segmentacao-pyannote-3.0.onnx",
        f"{_GITHUB}/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2",
        "24615ee884c897d9d2ba09bb4d30da6bb1b15e685065962db5b02e76e4996488",
        "sherpa-onnx-pyannote-segmentation-3-0/model.onnx",
    ),
    "voz": (
        "wespeaker-resnet34-voxceleb.onnx",
        f"{_GITHUB}/speaker-recongition-models/wespeaker_en_voxceleb_resnet34_LM.onnx",
        "e9848563da86f263117134dfd7ad63c92355b37de492b55e325400c9d9c39012",
        None,
    ),
}

# Distância a partir da qual duas vozes são consideradas pessoas diferentes, quando
# o número de pessoas não é informado. Calibrado em reuniões reais em português:
# valores menores "picotam" uma mesma pessoa em várias vozes.
LIMIAR_AGRUPAMENTO = 1.0

FIM_DE_FRASE = (".", "?", "!", "…")


# ------------------------------------------------------------------- modelos


def pasta_modelos() -> Path:
    """No executável os modelos já vêm junto; rodando do código, ficam no perfil do usuário."""
    if hasattr(sys, "_MEIPASS"):
        embutida = Path(sys._MEIPASS) / "modelos-falantes"
        if embutida.is_dir():
            return embutida
    base = os.environ.get("LOCALAPPDATA") or Path.home() / ".cache"
    return Path(base) / "MeetTranscript" / "modelos-falantes"


def _baixar(url: str, destino: Path, sha256: str) -> None:
    parcial = destino.with_name(destino.name + ".parcial")
    resumo = hashlib.sha256()
    try:
        with urllib.request.urlopen(url, timeout=60) as resposta, parcial.open("wb") as saida:
            while bloco := resposta.read(1 << 20):
                resumo.update(bloco)
                saida.write(bloco)
        if resumo.hexdigest() != sha256:
            raise RuntimeError(f"download corrompido: {url}")
        os.replace(parcial, destino)
    finally:
        parcial.unlink(missing_ok=True)


def garantir_modelos(log: Callable[[str], None] = print, aviso: str = "") -> dict[str, Path]:
    """Retorna o caminho de cada modelo, baixando o que faltar."""
    pasta = pasta_modelos()
    caminhos = {}
    for chave, (nome, url, sha256, membro) in MODELOS.items():
        caminho = pasta / nome
        if not caminho.exists():
            if aviso:
                log(aviso)
                aviso = ""
            pasta.mkdir(parents=True, exist_ok=True)
            if membro is None:
                _baixar(url, caminho, sha256)
            else:
                pacote = pasta / (nome + ".tar.bz2")
                _baixar(url, pacote, sha256)
                try:
                    with tarfile.open(pacote, "r:bz2") as tar:
                        dados = tar.extractfile(membro).read()
                    caminho.with_name(nome + ".parcial").write_bytes(dados)
                    os.replace(caminho.with_name(nome + ".parcial"), caminho)
                finally:
                    pacote.unlink(missing_ok=True)
        caminhos[chave] = caminho
    return caminhos


# ---------------------------------------------------------------- diarização


@dataclass
class Trecho:
    inicio: float
    fim: float
    falante: int


class Diarizador:
    def __init__(self, modelos: dict[str, Path], threads: int) -> None:
        import sherpa_onnx

        self._sherpa = sherpa_onnx
        self._modelos = modelos
        self._threads = threads

    def processar(
        self,
        audio: np.ndarray,
        pessoas: Optional[int] = None,
        progresso: Optional[Callable[[float], None]] = None,
        cancelado: Optional[Callable[[], bool]] = None,
        erro_cancelamento: type[BaseException] = KeyboardInterrupt,
    ) -> list[Trecho]:
        """pessoas=None descobre quantas pessoas falam; um número fixo melhora o resultado."""
        so = self._sherpa
        config = so.OfflineSpeakerDiarizationConfig(
            segmentation=so.OfflineSpeakerSegmentationModelConfig(
                pyannote=so.OfflineSpeakerSegmentationPyannoteModelConfig(
                    model=str(self._modelos["segmentacao"])
                ),
                num_threads=self._threads,
            ),
            embedding=so.SpeakerEmbeddingExtractorConfig(
                model=str(self._modelos["voz"]), num_threads=self._threads
            ),
            clustering=so.FastClusteringConfig(
                num_clusters=pessoas or -1, threshold=LIMIAR_AGRUPAMENTO
            ),
            min_duration_on=0.3,
            min_duration_off=0.5,
        )
        diarizacao = so.OfflineSpeakerDiarization(config)

        def acompanhar(feitos: int, total: int) -> int:
            # O sherpa-onnx ignora o valor de retorno; uma exceção aqui interrompe o processamento.
            if cancelado and cancelado():
                raise erro_cancelamento()
            if progresso and total:
                progresso(feitos / total)
            return 0

        resultado = diarizacao.process(audio, callback=acompanhar).sort_by_start_time()
        return [Trecho(r.start, r.end, r.speaker) for r in resultado]


# ------------------------------------------------- junção com a transcrição


@dataclass
class Palavra:
    inicio: float
    fim: float
    texto: str
    segmento: int  # índice do segmento do Whisper de onde veio


@dataclass
class Fala:
    """Frase (ou pedaço de frase) atribuída a um falante."""

    inicio: float
    fim: float
    falante: Optional[int]
    segmento: int
    palavras: list[Palavra] = field(default_factory=list)

    @property
    def texto(self) -> str:
        return "".join(p.texto for p in self.palavras).strip()


def dividir_em_frases(palavras: list[Palavra]) -> list[Fala]:
    """Corta nos fins de frase e nas fronteiras de segmento do Whisper. A frase é a
    unidade que recebe um falante: atribuir palavra por palavra deixaria palavras
    soltas trocando de voz por imprecisão de alguns centésimos de segundo."""
    falas: list[Fala] = []
    atual: Optional[Fala] = None
    for palavra in palavras:
        if atual is None or palavra.segmento != atual.segmento:
            atual = Fala(palavra.inicio, palavra.fim, None, palavra.segmento)
            falas.append(atual)
        atual.palavras.append(palavra)
        atual.fim = palavra.fim
        if palavra.texto.strip().endswith(FIM_DE_FRASE):
            atual = None
    return falas


def atribuir_falantes(falas: list[Fala], trechos: list[Trecho]) -> None:
    """Cada frase fica com o falante que mais se sobrepõe às suas palavras. Sem
    sobreposição (fala curta que a diarização não pegou), fica com o trecho mais
    próximo no tempo."""
    if not trechos:
        return
    trechos = sorted(trechos, key=lambda x: x.inicio)
    inicios = [x.inicio for x in trechos]
    fim_maximo = np.maximum.accumulate([x.fim for x in trechos])  # para limitar a busca

    for fala in falas:
        tempo: dict[int, float] = {}
        for palavra in fala.palavras:
            # Trechos que podem se sobrepor: começam antes do fim da palavra; anda para
            # trás enquanto algum trecho anterior ainda pode terminar depois do início.
            i = bisect.bisect_left(inicios, palavra.fim) - 1
            while i >= 0 and fim_maximo[i] > palavra.inicio:
                trecho = trechos[i]
                sobreposicao = min(trecho.fim, palavra.fim) - max(trecho.inicio, palavra.inicio)
                if sobreposicao > 0:
                    tempo[trecho.falante] = tempo.get(trecho.falante, 0.0) + sobreposicao
                i -= 1
        if tempo:
            fala.falante = max(tempo, key=tempo.get)
            continue
        meio = (fala.inicio + fala.fim) / 2
        i = bisect.bisect_left(inicios, meio)
        vizinhos = trechos[max(0, i - 3): i + 1]
        mais_perto = min(vizinhos, key=lambda x: max(x.inicio - meio, meio - x.fim, 0.0))
        fala.falante = mais_perto.falante


def numerar_por_ordem(falas: list[Fala]) -> int:
    """Renumera para Voz 1 = quem falou primeiro, Voz 2 = o segundo... Retorna quantas vozes."""
    ordem: dict[int, int] = {}
    for fala in falas:
        if fala.falante is None:
            fala.falante = 0  # sem diarização (ex.: áudio sem fala detectada): uma voz só
        if fala.falante not in ordem:
            ordem[fala.falante] = len(ordem) + 1
        fala.falante = ordem[fala.falante]
    return len(ordem)


def paragrafos(falas: list[Fala], duracao_maxima: float = 60.0) -> list[Fala]:
    """Junta frases seguidas do mesmo falante em parágrafos para o .txt. Monólogos
    longos são quebrados a cada ~1 min, para a marcação de tempo continuar útil."""
    saida: list[Fala] = []
    for fala in falas:
        anterior = saida[-1] if saida else None
        if (
            anterior
            and anterior.falante == fala.falante
            and fala.fim - anterior.inicio <= duracao_maxima
        ):
            anterior.palavras += fala.palavras
            anterior.fim = fala.fim
        else:
            saida.append(Fala(fala.inicio, fala.fim, fala.falante, fala.segmento, list(fala.palavras)))
    return saida
