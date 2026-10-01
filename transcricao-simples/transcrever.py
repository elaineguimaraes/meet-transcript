"""
Transcrição local de gravações de reunião (OBS Studio ou qualquer vídeo/áudio).

Tudo roda na sua máquina com o faster-whisper: nenhum áudio é enviado para a nuvem.
Para cada arquivo da pasta são gerados, ao lado dele:
    <nome>.txt  -> texto corrido com marcação de tempo
    <nome>.srt  -> legenda, para revisar junto com o vídeo

Uso pela linha de comando:
    py transcrever.py "C:\\caminho\\da\\pasta"

Para a interface gráfica, use app.py (ou iniciar.bat).
"""

from __future__ import annotations

import os
import sys
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
    for base in map(Path, sys.path):
        nvidia = base / "nvidia"
        if not nvidia.is_dir():
            continue
        for bin_dir in nvidia.glob("*/bin"):
            os.add_dll_directory(str(bin_dir))
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ["PATH"]


_registrar_dlls_cuda()

from faster_whisper import WhisperModel  # noqa: E402

# ---------------------------------------------------------------- configuração

# GPU NVIDIA com 4 GB ou mais: "large-v3-turbo" em int8 é o melhor equilíbrio
# entre qualidade em português e velocidade.
MODELO_GPU, COMPUTE_GPU = "large-v3-turbo", "int8"

# Sem GPU: "medium" em int8 é o melhor custo-benefício na CPU.
MODELO_CPU, COMPUTE_CPU = "medium", "int8"

IDIOMA = "pt"
EXTENSOES = {".mkv", ".mp4", ".mov", ".flv", ".webm", ".m4a", ".mp3", ".wav"}

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


def carregar_modelo(log: Log = print) -> WhisperModel:
    """Tenta a GPU e faz um teste real (1 s de silêncio) para confirmar que o CUDA
    funciona de verdade; se qualquer coisa falhar, usa a CPU."""
    try:
        log(f"Carregando {MODELO_GPU} na GPU (na primeira vez baixa ~1,6 GB)...")
        modelo = WhisperModel(MODELO_GPU, device="cuda", compute_type=COMPUTE_GPU)
        import numpy as np

        list(modelo.transcribe(np.zeros(16000, dtype=np.float32), language=IDIOMA)[0])
        log("GPU ok.")
        return modelo
    except Exception as erro:  # noqa: BLE001
        log(f"GPU indisponível ({erro.__class__.__name__}: {erro})")
        log(f"Carregando {MODELO_CPU} na CPU (na primeira vez baixa ~1,5 GB)...")
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
) -> None:
    """Gera <video>.txt e <video>.srt. Escreve em arquivos .parcial e só renomeia no
    final, para que uma transcrição interrompida não seja confundida com uma pronta."""
    # O faster-whisper decodifica o áudio direto do vídeo (via PyAV), já em 16 kHz mono.
    segmentos, info = modelo.transcribe(
        str(video),
        language=IDIOMA,
        vad_filter=True,                      # corta silêncio, acelera bastante
        vad_parameters={"min_silence_duration_ms": 700},
        beam_size=5,
        condition_on_previous_text=False,     # evita o modelo entrar em loop
    )
    log(f"    duração {hms(info.duration)}, transcrevendo...")

    destino_txt, destino_srt = video.with_suffix(".txt"), video.with_suffix(".srt")
    parcial_txt = destino_txt.with_name(destino_txt.name + ".parcial")
    parcial_srt = destino_srt.with_name(destino_srt.name + ".parcial")

    try:
        with parcial_txt.open("w", encoding="utf-8") as txt, parcial_srt.open("w", encoding="utf-8") as srt:
            txt.write(f"# Transcrição: {video.name}\n\n")
            for i, seg in enumerate(segmentos, start=1):
                if cancelado and cancelado():
                    raise Cancelamento()
                texto = seg.text.strip()
                txt.write(f"[{hms(seg.start)}] {texto}\n")
                srt.write(f"{i}\n{srt_ts(seg.start)} --> {srt_ts(seg.end)}\n{texto}\n\n")
                if progresso and info.duration:
                    progresso(min(seg.end / info.duration, 1.0))
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
) -> int:
    """Transcreve todos os vídeos/áudios da pasta. Retorna quantos foram transcritos."""
    videos = listar_videos(pasta)
    if not videos:
        log(f"Nenhum vídeo ou áudio encontrado em {pasta}")
        return 0

    pendentes = [v for v in videos if refazer or not v.with_suffix(".txt").exists()]
    for video in videos:
        if video not in pendentes:
            log(f"[pulando] {video.name}: já existe {video.with_suffix('.txt').name}")
    if not pendentes:
        log("Nada a fazer: todos os arquivos já têm transcrição.")
        return 0

    return transcrever_arquivos(pendentes, log, progresso)


def transcrever_arquivos(
    videos: list[Path],
    log: Log = print,
    progresso: Optional[Progresso] = None,
    cancelado: Optional[Cancelado] = None,
) -> int:
    """Transcreve exatamente os arquivos informados (refaz se já houver .txt).
    Se cancelado() retornar True, levanta Cancelamento: os arquivos já concluídos
    ficam salvos e o que estava em andamento é descartado."""
    if not videos:
        return 0

    modelo = carregar_modelo(log)

    for n, video in enumerate(videos):
        if cancelado and cancelado():
            raise Cancelamento()
        log(f"[{n + 1}/{len(videos)}] {video.name}")
        inicio = time.monotonic()
        avancar = (lambda f, n=n: progresso(n, len(videos), f)) if progresso else None
        transcrever_arquivo(modelo, video, log, avancar, cancelado)
        log(f"    pronto em {hms(time.monotonic() - inicio)} -> {video.with_suffix('.txt').name}")

    log("Concluído.")
    return len(videos)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    pasta = Path(sys.argv[1]).expanduser()
    if not pasta.is_dir():
        print(f"Pasta não encontrada: {pasta}")
        sys.exit(1)

    transcrever_pasta(pasta)


if __name__ == "__main__":
    main()
