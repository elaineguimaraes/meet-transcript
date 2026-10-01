# Meet Transcript

[Português](README.md) | **English**

Automatic transcription of meeting recordings made with **OBS Studio** (or any video/audio file), running **100% locally**: no audio ever leaves your computer and there are no API costs.

Just pick the folder with your recordings and tick which files to transcribe (or all of them). Each one gets a timestamped `.txt` and an `.srt` subtitle file.

**Supported formats:** MKV, MP4, MOV, FLV, WEBM (video) and M4A, MP3, WAV (audio).

**Language:** detected automatically for each chunk, so meetings in English, Portuguese or a mix of both come out in the language that was spoken. You can also fix the language.

```
# Transcrição: reuniao-planejamento.mkv

[00:00:00] Bom dia, pessoal. Vamos começar pela pauta de hoje.
[00:00:04] Primeiro item é o cronograma da entrega.
[00:00:07] A tela de cadastro já está pronta para teste,
[00:00:10] falta só validar com o time de suporte.
```

> The interface is in Portuguese; the transcription language is detected automatically.

## ⬇️ Download for Windows (nothing to install)

On the **[latest release](https://github.com/elaineguimaraes/meet-transcript/releases/latest)** page, download:

| File | For |
|---|---|
| `MeetTranscript-Windows-NVIDIA.zip` | Computers with an NVIDIA graphics card (much faster) |
| `MeetTranscript-Windows.zip` | Any computer (runs on the CPU) |

Extract the `.zip` and double-click **`Meet Transcript.exe`**. No Python needed.

- The first time, Windows may show *"Windows protected your PC"*: click **More info → Run anyway**. The warning appears because the program has no paid code-signing certificate.
- On the first transcription, the model (~1.5 GB) is downloaded once. After that it works offline.

## Usage

1. Click **Escolher...** (Choose) and select the folder with your recordings.
2. Click files to tick them (everything starts unticked). Use **Filtrar por nome** (filter by name) to find a file; the **Marcar todos** / **Desmarcar todos** / **Marcar pendentes** (tick all / untick all / tick pending) buttons act on the filtered files. Ticking a file that was already transcribed redoes it.
3. In **Idioma** (Language), keep **Automático** (Automatic) or fix the meeting's language. Note: fixing the wrong language makes the model *translate* the speech.
4. Click **Transcrever** (Transcribe). **Cancelar** (Cancel), or closing the window, stops the run: finished files are kept and the one in progress is discarded.

## Versions

| Folder | What it does | Status |
|---|---|---|
| [`transcricao-simples/`](transcricao-simples/) | Transcribes meetings without separating speakers | ✅ available |
| `identificacao-de-falantes/` | Transcription with speaker labels (Voice 1, Voice 2…) | 🚧 in progress |

## Highlights

- **Privacy**: uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (OpenAI's Whisper reimplemented on CTranslate2) right on your machine.
- **GPU with automatic fallback**: checks for an NVIDIA GPU and the CUDA libraries, confirms with a real test run (`large-v3-turbo` model) and, if anything fails, falls back to the CPU (`medium` model) on its own.
- **Simple interface** built with Tkinter: pick a folder, filter by name, tick the files, see the total size selected, follow the progress and cancel at any time. Transcription runs on a background thread, so the window never freezes.
- **Resumable**: the list shows what has already been transcribed. Output is written to `.parcial` files and only renamed at the end, so an interrupted run never leaves a half-finished transcript that looks complete.
- **Fast**: voice activity detection (VAD) skips silence. On a GTX 1650 (4 GB), about 2 hours of meetings took about 13 minutes.
- **Automated releases**: on every `v*` tag, [GitHub Actions](.github/workflows/release.yml) builds the executables with PyInstaller (CPU and NVIDIA builds), smoke-tests them and publishes the release.

## Running from source

Requirements: [Python](https://www.python.org/downloads/) 3.9 to 3.13. Optional: NVIDIA GPU with 4 GB+ and driver 528 or newer. You don't need ffmpeg: audio is read straight from the video file.

1. Clone the project:
   ```
   git clone https://github.com/elaineguimaraes/meet-transcript.git
   ```
2. In the `transcricao-simples` folder, double-click **`instalar.bat`**. It installs the dependencies and, if it finds an NVIDIA GPU, CUDA support as well.
3. Double-click **`iniciar.bat`**.

The code also runs on Linux/macOS (`python app.py`).

### From the command line

```
cd transcricao-simples
py -m pip install -r requirements.txt
py -m pip install -r requirements-gpu.txt   # optional, NVIDIA GPU only
py transcrever.py "C:\path\to\recordings"
py transcrever.py "C:\path\to\recordings" --idioma en   # fix the language
```

With the executable, the equivalent is `meet-transcript-cli.exe "C:\path\to\recordings"`.

### Building the executable

```
cd transcricao-simples
py -m pip install pyinstaller
py -m PyInstaller meet_transcript.spec                 # CPU build
set MT_VARIANTE=nvidia && py -m PyInstaller meet_transcript.spec   # NVIDIA build
```

### Settings

Model, default language and accepted formats are at the top of [`transcrever.py`](transcricao-simples/transcrever.py) (`MODELO_GPU`, `MODELO_CPU`, `IDIOMA`, `EXTENSOES`).

## Troubleshooting

| Symptom | Fix |
|---|---|
| Translated passages (e.g. an English meeting coming out in Portuguese) | The language was fixed to the wrong one. Use **Automático** and transcribe again. |
| "GPU indisponível" (GPU unavailable) in the log | Expected on computers without an NVIDIA card: the program uses the CPU. If you have NVIDIA, use the "NVIDIA" download (or install `requirements-gpu.txt`) and check the driver (`nvidia-smi`, must be 528+). |
| `TypeError: open() got an unexpected keyword argument 'metadata_errors'` | PyAV is too new: `py -m pip install --only-binary=:all: "av<15"` |
| `python` opens the Microsoft Store | Use `py` instead of `python`, or turn off the shortcut in *Settings → Apps → Advanced app settings → App execution aliases* |

## Project structure

```
meet-transcript/
├── .github/workflows/release.yml  # builds and publishes the executables
└── transcricao-simples/
    ├── app.py                     # graphical interface (Tkinter)
    ├── transcrever.py             # transcription logic + command line
    ├── meet_transcript.spec       # PyInstaller recipe
    ├── LEIA-ME.txt                # quick guide shipped inside the .zip
    ├── instalar.bat / iniciar.bat
    ├── requirements.txt
    └── requirements-gpu.txt       # optional CUDA
```
