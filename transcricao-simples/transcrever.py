"""
Transcrição local de gravações de reunião (OBS Studio ou qualquer vídeo/áudio).

Tudo roda na sua máquina com o faster-whisper: nenhum áudio é enviado para a nuvem.
Para cada arquivo da pasta é gerado, na subpasta "transcrições":
    <nome>.txt  -> texto corrido com marcação de tempo

Uso pela linha de comando:
    py transcrever.py "C:\\caminho\\da\\pasta"
    py transcrever.py "C:\\caminho\\da\\pasta" --idioma en

Sem --idioma, o idioma é detectado automaticamente a cada trecho.

Para a interface gráfica, use app.py (ou iniciar.bat).
"""

from __future__ import annotations

import os
import sys
import tempfile
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

from faster_whisper import WhisperModel  # noqa: E402

from textos import t  # noqa: E402

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
# Subpasta (dentro da pasta das gravações) onde ficam os .txt gerados.
PASTA_SAIDA = "transcrições"

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


def listar_videos(pasta: Path) -> list[Path]:
    return sorted(p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in EXTENSOES)


def saida(video: Path) -> Path:
    """Base dos arquivos gerados para o vídeo: <pasta>/transcrições/<nome do vídeo>."""
    return video.parent / PASTA_SAIDA / video.name


def ja_transcrito(video: Path) -> bool:
    # Versões anteriores salvavam o .txt ao lado do vídeo; esses também contam.
    return saida(video).with_suffix(".txt").exists() or video.with_suffix(".txt").exists()


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
        # os.cpu_count() conta threads lógicas; metade ≈ núcleos físicos, que é o
        # que rende melhor no CTranslate2.
        nucleos = max(1, (os.cpu_count() or 2) // 2)
        return WhisperModel(MODELO_CPU, device="cpu", compute_type=COMPUTE_CPU, cpu_threads=nucleos)


def transcrever_arquivo(
    modelo: WhisperModel,
    video: Path,
    log: Log = print,
    progresso: Optional[Callable[[float], None]] = None,
    cancelado: Optional[Cancelado] = None,
    idioma: Optional[str] = IDIOMA,
    destino: Optional[Path] = None,
) -> None:
    """Gera transcrições/<video>.txt (ou <destino>.txt, se informado). Escreve em um
    arquivo .parcial e só renomeia no final, para que uma transcrição interrompida não
    seja confundida com uma pronta."""
    # O faster-whisper decodifica o áudio direto do vídeo (via PyAV), já em 16 kHz mono.
    segmentos, info = modelo.transcribe(
        str(video),
        language=idioma,
        multilingual=idioma is None,          # sem idioma fixo, detecta a cada trecho
        vad_filter=True,                      # corta silêncio, acelera bastante
        vad_parameters={"min_silence_duration_ms": 700},
        beam_size=5,
        condition_on_previous_text=False,     # evita o modelo entrar em loop
    )
    detectado = t("idioma_auto", codigo=info.language) if idioma is None else idioma
    log(t("duracao", duracao=hms(info.duration), idioma=detectado))

    base = destino or saida(video)
    base.parent.mkdir(exist_ok=True)
    destino_txt = base.with_suffix(".txt")
    parcial_txt = destino_txt.with_name(destino_txt.name + ".parcial")

    try:
        with parcial_txt.open("w", encoding="utf-8") as txt:
            txt.write(t("cabecalho", nome=video.name) + "\n\n")
            for seg in segmentos:
                if cancelado and cancelado():
                    raise Cancelamento()
                txt.write(f"[{hms(seg.start)}] {seg.text.strip()}\n")
                if progresso and info.duration:
                    progresso(min(seg.end / info.duration, 1.0))
        os.replace(parcial_txt, destino_txt)
    finally:
        parcial_txt.unlink(missing_ok=True)


def transcrever_pasta(
    pasta: Path,
    log: Log = print,
    progresso: Optional[Progresso] = None,
    refazer: bool = False,
    idioma: Optional[str] = IDIOMA,
) -> int:
    """Transcreve todos os vídeos/áudios da pasta. Retorna quantos foram transcritos."""
    videos = listar_videos(pasta)
    if not videos:
        log(t("nenhum_video", pasta=pasta))
        return 0

    pendentes = [v for v in videos if refazer or not ja_transcrito(v)]
    for video in videos:
        if video not in pendentes:
            log(t("pulando", nome=video.name))
    if not pendentes:
        log(t("nada_a_fazer"))
        return 0

    return transcrever_arquivos(pendentes, log, progresso, idioma=idioma)


def _bloco(video: Path, txt: Path) -> str:
    """Trecho de um arquivo dentro do .txt único: título com nome e data, e as falas
    (sem a linha de cabeçalho do .txt individual)."""
    corpo = txt.read_text(encoding="utf-8").split("\n", 1)[1].strip()
    data = time.strftime(t("formato_data"), time.localtime(video.stat().st_mtime))
    return t("secao", nome=video.name, data=data) + "\n\n" + corpo


def _salvar_unico(destino: Path, blocos: list[str]) -> None:
    destino.parent.mkdir(exist_ok=True)
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
    unico: Optional[Path] = None,
) -> int:
    """Transcreve exatamente os arquivos informados (refaz se já houver .txt).
    Se cancelado() retornar True, levanta Cancelamento: os arquivos já concluídos
    ficam salvos e o que estava em andamento é descartado.

    Com unico, junta as transcrições (na ordem recebida) nesse único .txt em vez de
    criar um .txt para cada arquivo."""
    if not videos:
        return 0

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
                base = Path(temporaria) / video.name if unico else saida(video)
                transcrever_arquivo(modelo, video, log, avancar, cancelado, idioma, base)
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


def main() -> None:
    args = sys.argv[1:]
    idioma = IDIOMA
    if "--idioma" in args:
        i = args.index("--idioma")
        idioma = args[i + 1] if i + 1 < len(args) else None
        del args[i:i + 2]
    if not args:
        prog = "meet-transcript-cli.exe" if getattr(sys, "frozen", False) else "py transcrever.py"
        print(t("uso", prog=prog))
        sys.exit(1)

    pasta = Path(args[0]).expanduser()
    if not pasta.is_dir():
        print(t("pasta_nao_encontrada", pasta=pasta))
        sys.exit(1)

    transcrever_pasta(pasta, idioma=idioma)


if __name__ == "__main__":
    main()
