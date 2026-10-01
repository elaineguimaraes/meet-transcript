# Meet Transcript

[Português](README.md) | **English**

Automatic transcription of meeting recordings made with **OBS Studio** (or any video/audio file), running **100% locally**: no audio ever leaves your computer and there are no API costs.

Just pick the folder with your recordings and tick which files to transcribe (or all of them). Each one gets a timestamped `.txt` and an `.srt` subtitle file.

**Supported formats:** MKV, MP4, MOV, FLV, WEBM (video) and M4A, MP3, WAV (audio).

```
# Transcrição: reuniao-planejamento.mkv

[00:00:00] Bom dia, pessoal. Vamos começar pela pauta de hoje.
[00:00:04] Primeiro item é o cronograma da entrega.
[00:00:07] A tela de cadastro já está pronta para teste,
[00:00:10] falta só validar com o time de suporte.
```

> The interface and the default transcription language are Portuguese. To transcribe other languages, change `IDIOMA` (e.g. `"en"`) at the top of `transcrever.py`.

## Versions

| Folder | What it does | Status |
|---|---|---|
| [`transcricao-simples/`](transcricao-simples/) | Transcribes meetings without separating speakers | ✅ available |
| `identificacao-de-falantes/` | Transcription with speaker labels (Voice 1, Voice 2…) | 🚧 in progress |

## Highlights

- **Privacy**: uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (OpenAI's Whisper reimplemented on CTranslate2) right on your machine.
- **GPU with automatic fallback**: tries the NVIDIA GPU (`large-v3-turbo` model) and checks it with a real test run. If CUDA fails, it falls back to the CPU (`medium` model) on its own.
- **Simple interface** built with Tkinter: pick a folder, filter by name, tick the files (all, none or only pending ones), see the total size selected, follow the progress and cancel at any time. Transcription runs on a background thread, so the window never freezes.
- **Resumable**: the list shows what has already been transcribed, and the command line skips those files. Output is written to `.parcial` files and only renamed at the end, so an interrupted run never leaves a half-finished transcript that looks complete.
- **Fast**: voice activity detection (VAD) skips silence. On a GTX 1650 (4 GB), about 2 hours of meetings took about 13 minutes.

## Requirements

- Windows 10/11 (the code also runs on Linux/macOS from the command line or the interface)
- [Python](https://www.python.org/downloads/) 3.9 to 3.13
- Optional: NVIDIA GPU with 4 GB+ and driver 528 or newer. Without a GPU it runs on the CPU, just more slowly.

You don't need to install ffmpeg: audio is read straight from the video file.

## Usage

1. Download the project (**Code → Download ZIP**) or clone it:
   ```
   git clone https://github.com/elaineguimaraes/meet-transcript.git
   ```
2. In the `transcricao-simples` folder, double-click **`instalar.bat`**. It installs the dependencies and, if it finds an NVIDIA GPU, CUDA support as well.
3. Double-click **`iniciar.bat`** and choose the folder with your recordings.
4. Click files to tick them (everything starts unticked). Use **Filtrar por nome** (filter by name) to find a file; the **Marcar todos** / **Desmarcar todos** / **Marcar pendentes** (tick all / untick all / tick pending) buttons act on the filtered files. Ticking a file that was already transcribed redoes it.
5. Click **Transcrever** (Transcribe). **Cancelar** (Cancel), or closing the window, stops the run: finished files are kept and the one in progress is discarded.

The model (~1.5 GB) is downloaded on the first run, only once.

### From the command line

```
cd transcricao-simples
py -m pip install -r requirements.txt
py -m pip install -r requirements-gpu.txt   # optional, NVIDIA GPU only
py transcrever.py "C:\path\to\recordings"
```

### Settings

Model, language and accepted formats are at the top of [`transcrever.py`](transcricao-simples/transcrever.py) (`MODELO_GPU`, `MODELO_CPU`, `IDIOMA`, `EXTENSOES`).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `TypeError: open() got an unexpected keyword argument 'metadata_errors'` | PyAV is too new: `py -m pip install --only-binary=:all: "av<15"` |
| "GPU indisponível" (GPU unavailable) in the log | Check the NVIDIA driver (`nvidia-smi`, must be 528+) and that `requirements-gpu.txt` was installed. The program carries on with the CPU anyway. |
| `python` opens the Microsoft Store | Use `py` instead of `python`, or turn off the shortcut in *Settings → Apps → Advanced app settings → App execution aliases* |

## Project structure

```
meet-transcript/
└── transcricao-simples/
    ├── app.py                 # graphical interface (Tkinter)
    ├── transcrever.py         # transcription logic + command line
    ├── instalar.bat / iniciar.bat
    ├── requirements.txt
    └── requirements-gpu.txt   # optional CUDA
```
