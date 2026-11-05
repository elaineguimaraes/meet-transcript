"""
Transcrição local de gravações de reunião com identificação de quem fala
(Voz 1, Voz 2...).

Tudo roda na sua máquina: o faster-whisper transcreve e o sherpa-onnx separa as
vozes (veja falantes.py). Nenhum áudio é enviado para a nuvem.
Para cada arquivo da pasta são gerados, ao lado dele:
    <nome>.txt  -> falas com marcação de tempo e quem falou
    <nome>.srt  -> legenda com o falante, para revisar junto com o vídeo

Uso pela linha de comando:
    py transcrever.py "C:\\caminho\\da\\pasta"
    py transcrever.py "C:\\caminho\\da\\pasta" --idioma en --pessoas 3

Sem --idioma, o idioma é detectado automaticamente a cada trecho. Sem --pessoas,
o número de pessoas é descoberto automaticamente; informar melhora o resultado.

Para a interface gráfica, use app.py (ou iniciar.bat).
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Optional

# Evita que o download do modelo trave no Windows e silencia um aviso inofensivo
# do cache do Hugging Face (symlinks exigem modo desenvolvedor no Windows).
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


def _registrar_dlls_cuda() -> None:
    """No Windows, as DLLs do CUDA instaladas via pip ficam em site-packages/nvidia/*/bin
    e o Python não as encontra sozinho. Aqui elas são adicionadas ao caminho de busca."""
    if os.name != "nt":
        return
    # No executável (PyInstaller), as DLLs ficam dentro da pasta _internal (sys._MEIPASS).
    bases = sys.path + ([sys._MEIPASS] if hasattr(sys, "_MEIPASS") else [])
    for base in map(Path, bases):
        nvidia = base / "nvidia"
        if not nvidia.is_dir():
            continue
        for bin_dir in nvidia.glob("*/bin"):
            os.add_dll_directory(str(bin_dir))
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ["PATH"]


_registrar_dlls_cuda()

from faster_whisper import WhisperModel, decode_audio  # noqa: E402

import falantes  # noqa: E402
from textos import t  # noqa: E402

# falantes.py só importa o sherpa-onnx na hora de separar as vozes; sem ele instalado,
# a interface já avisa ao abrir (e sugere o instalar.bat) em vez de falhar no meio.
if importlib.util.find_spec("sherpa_onnx") is None:
    raise ModuleNotFoundError("No module named 'sherpa_onnx'", name="sherpa_onnx")

# ---------------------------------------------------------------- configuração

# GPU NVIDIA com 4 GB ou mais: "large-v3-turbo" em int8 é o melhor equilíbrio
# entre qualidade em português e velocidade.
MODELO_GPU, COMPUTE_GPU = "large-v3-turbo", "int8"

# Sem GPU: "medium" em int8 é o melhor custo-benefício na CPU.
MODELO_CPU, COMPUTE_CPU = "medium", "int8"

# None = detecta o idioma a cada trecho (~30 s), o que também atende reuniões que
# misturam idiomas. Fixar um código ("pt", "en"...) evita erro de detecção quando a
# reunião é toda em um idioma; mas fixar o idioma errado faz o modelo TRADUZIR a fala.
IDIOMA: Optional[str] = None
# .ogg e .opus: áudios do WhatsApp (mensagens de voz).
EXTENSOES = {".mkv", ".mp4", ".mov", ".flv", ".webm", ".m4a", ".mp3", ".wav", ".ogg", ".opus"}

# os.cpu_count() conta threads lógicas; metade ≈ núcleos físicos, que é o que rende
# melhor tanto no CTranslate2 quanto no ONNX Runtime.
NUCLEOS = max(1, (os.cpu_count() or 2) // 2)

Log = Callable[[str], None]
# (indice do arquivo, total de arquivos, fração concluída do arquivo atual)
Progresso = Callable[[int, int, float], None]
# Consultada durante o trabalho; se retornar True, a transcrição é interrompida.
Cancelado = Callable[[], bool]


class Cancelamento(Exception):
    """Transcrição interrompida a pedido do usuário."""

# --------------------------------------------------------------------- funções


def hms(segundos: float) -> str:
    h, resto = divmod(int(segundos), 3600)
    m, s = divmod(resto, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def srt_ts(segundos: float) -> str:
    ms = int((segundos - int(segundos)) * 1000)
    return hms(segundos) + f",{ms:03d}"


def listar_videos(pasta: Path) -> list[Path]:
    return sorted(p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in EXTENSOES)


def _motivo_sem_gpu() -> Optional[str]:
    """Retorna por que a GPU não pode ser usada, ou None se ela parece utilizável."""
    import ctranslate2

    if ctranslate2.get_cuda_device_count() == 0:
        return t("sem_gpu")
    if os.name == "nt":
        import ctypes

        for dll in ("cublas64_12.dll", "cudnn64_9.dll"):
            try:
                ctypes.WinDLL(dll)
            except OSError:
                return t("sem_dll", dll=dll)
    return None


def carregar_modelo(log: Log = print) -> WhisperModel:
    """Tenta a GPU e faz um teste real (1 s de silêncio) para confirmar que o CUDA
    funciona de verdade; se qualquer coisa falhar, usa a CPU."""
    try:
        # Checa antes de tentar: sem as DLLs do CUDA, o CTranslate2 pode derrubar o
        # processo inteiro em vez de levantar uma exceção.
        motivo = _motivo_sem_gpu()
        if motivo:
            raise RuntimeError(motivo)
        log(t("carregando_gpu", modelo=MODELO_GPU))
        modelo = WhisperModel(MODELO_GPU, device="cuda", compute_type=COMPUTE_GPU)
        import numpy as np

        list(modelo.transcribe(np.zeros(16000, dtype=np.float32), language="en")[0])
        log(t("gpu_ok"))
        return modelo
    except Exception as erro:  # noqa: BLE001
        log(t("gpu_indisponivel", erro=f"{erro.__class__.__name__}: {erro}"))
        log(t("carregando_cpu", modelo=MODELO_CPU))
        return WhisperModel(MODELO_CPU, device="cpu", compute_type=COMPUTE_CPU, cpu_threads=NUCLEOS)


def carregar_diarizador(log: Log = print) -> falantes.Diarizador:
    modelos = falantes.garantir_modelos(log, aviso=t("baixando_vozes"))
    return falantes.Diarizador(modelos, threads=NUCLEOS)


def _transcrever_palavras(
    modelo: WhisperModel,
    audio,
    idioma: Optional[str],
    log: Log,
    progresso: Callable[[float], None],
    cancelado: Optional[Cancelado],
) -> list[falantes.Palavra]:
    segmentos, info = modelo.transcribe(
        audio,
        language=idioma,
        multilingual=idioma is None,          # sem idioma fixo, detecta a cada trecho
        vad_filter=True,                      # corta silêncio, acelera bastante
        vad_parameters={"min_silence_duration_ms": 700},
        beam_size=5,
        condition_on_previous_text=False,     # evita o modelo entrar em loop
        word_timestamps=True,                 # tempo de cada palavra, para casar com as vozes
    )
    detectado = t("idioma_auto", codigo=info.language) if idioma is None else idioma
    log(t("duracao", duracao=hms(info.duration), idioma=detectado))

    palavras = []
    for i, seg in enumerate(segmentos):
        if cancelado and cancelado():
            raise Cancelamento()
        for p in seg.words or []:
            palavras.append(falantes.Palavra(p.start, p.end, p.word, i))
        if info.duration:
            progresso(min(seg.end / info.duration, 1.0))
    progresso(1.0)
    return palavras


def transcrever_arquivo(
    modelo: WhisperModel,
    diarizador: falantes.Diarizador,
    video: Path,
    log: Log = print,
    progresso: Optional[Callable[[float], None]] = None,
    cancelado: Optional[Cancelado] = None,
    idioma: Optional[str] = IDIOMA,
    pessoas: Optional[int] = None,
    destino: Optional[Path] = None,
) -> None:
    """Gera <video>.txt e <video>.srt (ou <destino>.txt/.srt, se informado) com o
    falante de cada trecho. Escreve em arquivos .parcial e só renomeia no final, para
    que uma transcrição interrompida não seja confundida com uma pronta."""
    # O áudio é decodificado uma vez (16 kHz mono) e usado pelas duas etapas.
    audio = decode_audio(str(video), sampling_rate=falantes.TAXA)

    fracao = {"texto": 0.0, "vozes": 0.0}
    na_gpu = modelo.model.device == "cuda"
    # Na GPU a transcrição é rápida e as vozes rodam ao mesmo tempo, na CPU; só com a
    # CPU as duas etapas disputariam os mesmos núcleos, então rodam uma depois da outra.
    peso_vozes = 0.5 if na_gpu else 0.25

    def avancar(etapa: str, valor: float) -> None:
        fracao[etapa] = valor
        if progresso:
            progresso(peso_vozes * fracao["vozes"] + (1 - peso_vozes) * fracao["texto"])

    resultado: dict[str, object] = {}
    parar = threading.Event()  # interrompe as vozes se a transcrição falhar

    def separar_vozes() -> None:
        try:
            resultado["trechos"] = diarizador.processar(
                audio,
                pessoas,
                lambda f: avancar("vozes", f),
                lambda: parar.is_set() or bool(cancelado and cancelado()),
                Cancelamento,
            )
        except BaseException as erro:  # noqa: BLE001  (repassado para a thread principal)
            resultado["erro"] = erro

    log(t("identificando_vozes"))
    paralelo = threading.Thread(target=separar_vozes, daemon=True) if na_gpu else None
    if paralelo:
        paralelo.start()
    else:
        separar_vozes()
        if "erro" in resultado:
            raise resultado["erro"]

    try:
        palavras = _transcrever_palavras(
            modelo, audio, idioma, log, lambda f: avancar("texto", f), cancelado
        )
    except BaseException:
        parar.set()
        raise
    finally:
        if paralelo:
            paralelo.join()  # se houve cancelamento, a outra thread também para logo
    if "erro" in resultado:
        raise resultado["erro"]

    falas = falantes.dividir_em_frases(palavras)
    falantes.atribuir_falantes(falas, resultado["trechos"])
    vozes = falantes.numerar_por_ordem(falas)
    log(t("vozes_encontradas", n=vozes))

    base = destino or video
    destino_txt, destino_srt = base.with_suffix(".txt"), base.with_suffix(".srt")
    parcial_txt = destino_txt.with_name(destino_txt.name + ".parcial")
    parcial_srt = destino_srt.with_name(destino_srt.name + ".parcial")

    try:
        with parcial_txt.open("w", encoding="utf-8") as txt:
            txt.write(t("cabecalho", nome=video.name) + "\n")
            txt.write(t("cabecalho_vozes", n=vozes) + "\n\n")
            for fala in falantes.paragrafos(falas):
                txt.write(f"[{hms(fala.inicio)}] {t('voz', n=fala.falante)}: {fala.texto}\n\n")
        with parcial_srt.open("w", encoding="utf-8") as srt:
            for i, fala in enumerate(falantes.legendas(falas), start=1):
                srt.write(
                    f"{i}\n{srt_ts(fala.inicio)} --> {srt_ts(fala.fim)}\n"
                    f"{t('voz', n=fala.falante)}: {fala.texto}\n\n"
                )
        os.replace(parcial_srt, destino_srt)
        os.replace(parcial_txt, destino_txt)
    finally:
        parcial_txt.unlink(missing_ok=True)
        parcial_srt.unlink(missing_ok=True)


def transcrever_pasta(
    pasta: Path,
    log: Log = print,
    progresso: Optional[Progresso] = None,
    refazer: bool = False,
    idioma: Optional[str] = IDIOMA,
    pessoas: Optional[int] = None,
) -> int:
    """Transcreve todos os vídeos/áudios da pasta. Retorna quantos foram transcritos."""
    videos = listar_videos(pasta)
    if not videos:
        log(t("nenhum_video", pasta=pasta))
        return 0

    pendentes = [v for v in videos if refazer or not v.with_suffix(".txt").exists()]
    for video in videos:
        if video not in pendentes:
            log(t("pulando", nome=video.name, txt=video.with_suffix(".txt").name))
    if not pendentes:
        log(t("nada_a_fazer"))
        return 0

    return transcrever_arquivos(pendentes, log, progresso, idioma=idioma, pessoas=pessoas)


def _bloco(video: Path, txt: Path) -> str:
    """Trecho de um arquivo dentro do .txt único: título com nome e data, e as falas
    (sem a linha de cabeçalho do .txt individual)."""
    corpo = txt.read_text(encoding="utf-8").split("\n", 1)[1].strip()
    data = time.strftime(t("formato_data"), time.localtime(video.stat().st_mtime))
    return t("secao", nome=video.name, data=data) + "\n\n" + corpo


def _salvar_unico(destino: Path, blocos: list[str]) -> None:
    parcial = destino.with_name(destino.name + ".parcial")
    try:
        with parcial.open("w", encoding="utf-8") as txt:
            txt.write(t("cabecalho_unico", n=len(blocos)) + "\n\n" + "\n\n".join(blocos) + "\n")
        os.replace(parcial, destino)
    finally:
        parcial.unlink(missing_ok=True)


def transcrever_arquivos(
    videos: list[Path],
    log: Log = print,
    progresso: Optional[Progresso] = None,
    cancelado: Optional[Cancelado] = None,
    idioma: Optional[str] = IDIOMA,
    pessoas: Optional[int] = None,
    unico: Optional[Path] = None,
) -> int:
    """Transcreve exatamente os arquivos informados (refaz se já houver .txt).
    Se cancelado() retornar True, levanta Cancelamento: os arquivos já concluídos
    ficam salvos e o que estava em andamento é descartado.

    Com unico, junta as transcrições (na ordem recebida) nesse único .txt em vez de
    criar um .txt e um .srt ao lado de cada arquivo."""
    if not videos:
        return 0

    diarizador = carregar_diarizador(log)
    modelo = carregar_modelo(log)

    # Com unico, cada arquivo é transcrito numa pasta temporária e o texto vai para
    # a lista de blocos; assim nenhum .txt individual existente é tocado.
    blocos: list[str] = []
    with tempfile.TemporaryDirectory() as temporaria:
        try:
            for n, video in enumerate(videos):
                if cancelado and cancelado():
                    raise Cancelamento()
                log(f"[{n + 1}/{len(videos)}] {video.name}")
                inicio = time.monotonic()
                avancar = (lambda f, n=n: progresso(n, len(videos), f)) if progresso else None
                base = Path(temporaria) / video.name if unico else video
                transcrever_arquivo(modelo, diarizador, video, log, avancar, cancelado, idioma, pessoas, base)
                if unico:
                    blocos.append(_bloco(video, base.with_suffix(".txt")))
                pronto = unico or base.with_suffix(".txt")
                log(t("arquivo_pronto", tempo=hms(time.monotonic() - inicio), arquivo=pronto.name))
        except Cancelamento:
            if blocos:  # o que já ficou pronto é salvo no .txt único
                _salvar_unico(unico, blocos)
                log(t("unico_parcial", n=len(blocos), arquivo=unico.name))
            raise
    if unico:
        _salvar_unico(unico, blocos)
        log(t("unico_pronto", arquivo=unico.name))

    log(t("concluido"))
    return len(videos)


def _tirar_opcao(args: list[str], nome: str) -> Optional[str]:
    if nome not in args:
        return None
    i = args.index(nome)
    valor = args[i + 1] if i + 1 < len(args) else None
    del args[i:i + 2]
    return valor


def main() -> None:
    args = sys.argv[1:]
    idioma = _tirar_opcao(args, "--idioma") or IDIOMA
    pessoas = _tirar_opcao(args, "--pessoas")
    if not args or (pessoas is not None and not pessoas.isdigit()):
        prog = "meet-transcript-cli.exe" if getattr(sys, "frozen", False) else "py transcrever.py"
        print(t("uso", prog=prog))
        sys.exit(1)

    pasta = Path(args[0]).expanduser()
    if not pasta.is_dir():
        print(t("pasta_nao_encontrada", pasta=pasta))
        sys.exit(1)

    transcrever_pasta(pasta, idioma=idioma, pessoas=int(pessoas) if pessoas else None)


if __name__ == "__main__":
    main()
