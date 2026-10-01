# -*- mode: python ; coding: utf-8 -*-
"""
Receita do PyInstaller para gerar a pasta "Meet Transcript" com dois executáveis:
    Meet Transcript.exe      -> interface gráfica
    meet-transcript-cli.exe  -> linha de comando

    pyinstaller meet_transcript.spec                    (versão CPU)
    set MT_VARIANTE=nvidia && pyinstaller meet_transcript.spec   (inclui o CUDA, ~2 GB)

O GitHub Actions (.github/workflows/release.yml) roda isto a cada tag v*.
"""
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

VARIANTE = os.environ.get("MT_VARIANTE", "cpu")

datas, binaries, hiddenimports = [], [], ["transcrever"]
for pacote in ("faster_whisper", "ctranslate2", "av", "onnxruntime", "tokenizers"):
    d, b, h = collect_all(pacote)
    datas, binaries, hiddenimports = datas + d, binaries + b, hiddenimports + h

# DLLs do CUDA (pacotes nvidia-*-cu12), mantendo a estrutura nvidia/<pacote>/bin que o
# transcrever.py procura ao iniciar.
binarios_cuda = []
if VARIANTE == "nvidia":
    import nvidia

    for base in map(Path, nvidia.__path__):
        for dll in base.glob("*/bin/*.dll"):
            if not dll.name.startswith("nvblas"):  # não usada
                binarios_cuda.append((str(dll), f"nvidia/{dll.parent.parent.name}/bin"))

EXCLUIR = ["torch", "tensorflow", "transformers", "matplotlib", "pandas", "IPython", "PIL"]


def analisar(script, extras=()):
    return Analysis(
        [script],
        binaries=binaries + list(extras),
        datas=datas,
        hiddenimports=hiddenimports,
        excludes=EXCLUIR,
    )


a_app = analisar("app.py", binarios_cuda)
a_cli = analisar("transcrever.py")

exe_app = EXE(
    PYZ(a_app.pure), a_app.scripts, [],
    exclude_binaries=True, name="Meet Transcript", console=False, upx=False,
)
exe_cli = EXE(
    PYZ(a_cli.pure), a_cli.scripts, [],
    exclude_binaries=True, name="meet-transcript-cli", console=True, upx=False,
)
COLLECT(
    exe_app, a_app.binaries, a_app.datas,
    exe_cli, a_cli.binaries, a_cli.datas,
    name="Meet Transcript", upx=False,
)
