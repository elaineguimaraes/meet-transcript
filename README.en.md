# Meet Transcript

[Português](README.md) | **English**

Automatic transcription of meeting recordings made with **OBS Studio**, **WhatsApp voice messages** or any video/audio file, running **100% locally**: no audio ever leaves your computer and there are no API costs.

Just pick the folder with your recordings and tick which files to transcribe (or all of them). Each one gets a timestamped `.txt` and an `.srt` subtitle file.

**Supported formats:** MKV, MP4, MOV, FLV, WEBM (video) and M4A, MP3, WAV, OGG, OPUS (audio, including WhatsApp voice messages).

**Language:** detected automatically for each chunk, so meetings in English, Portuguese or a mix of both come out in the language that was spoken. You can also fix the language.

```
# Transcrição: reuniao-planejamento.mkv

[00:00:00] Bom dia, pessoal. Vamos começar pela pauta de hoje.
[00:00:04] Primeiro item é o cronograma da entrega.
[00:00:07] A tela de cadastro já está pronta para teste,
[00:00:10] falta só validar com o time de suporte.
```

> The interface is available in English and Portuguese (it follows your Windows language; switch in the top-right corner). The transcription language is detected automatically.

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

1. Click **Browse...** and select the folder with your recordings. Next time, the program opens in that folder.
2. Click files to tick them (everything starts unticked). The list shows each file's last modified date; the list starts with the most recent ones; click the **File** or **Modified** column header to change the order (click again to reverse). Use **Filter by name** to find a file; the **Select all** / **Select none** / **Select pending** buttons act on the filtered files. Ticking a file that was already transcribed redoes it.
3. To get everything in one file, tick **Combine into a single .txt**: the transcripts come one after the other, in list order, in `Combined transcript <date and time>.txt` (no `.srt`). Unticked, each file gets its own `.txt` and `.srt`.
4. In **Spoken language**, keep **Automatic** or fix the meeting's language. Note: fixing the wrong language makes the model *translate* the speech.
5. Click **Transcribe**. **Cancel**, or closing the window, stops the run: finished files are kept (in the single `.txt`, if that option is ticked) and the one in progress is discarded.

## WhatsApp voice messages

When a client follows up on a meeting by sending voice messages on WhatsApp, you can transcribe them the same way:

1. Download the audios to a folder (in WhatsApp Web or Desktop: message menu → **Download**). They come as `.ogg` (or `.opus` when exported from a phone).
2. Pick that folder in the program, sort by **File**, tick the audios and click **Transcribe**. Each audio gets its own `.txt` or, with **Combine into a single .txt** ticked, they all go into one file, each under its own heading:

```
# Combined transcript: 2 file(s)

## WhatsApp Ptt 2026-11-04 at 10.17.56.ogg (modified 2026-11-04 10:18)

[00:00:00] Hi, good morning! I checked the documents, they're all in the folder.

## WhatsApp Ptt 2026-11-04 at 10.20.06.ogg (modified 2026-11-04 10:21)

[00:00:00] Let me try to explain the approval flow here.
```

Tip: the downloaded file name already contains the time it was sent (`WhatsApp Ptt 2026-11-04 at 10.17.56.ogg`), so sorting by **File** puts the messages in chronological order. The **Modified** column shows when the file was saved to your computer, which may be well after it was sent.

## Versions

| Folder | What it does | Status |
|---|---|---|
| [`transcricao-simples/`](transcricao-simples/) | Transcribes meetings without separating speakers | ✅ available |
| [`identificacao-de-falantes/`](identificacao-de-falantes/) | Transcription with speaker labels (Speaker 1, Speaker 2…) | 🧪 testing (from source) |

### Speaker identification (testing)

Same interface, with one extra selector: **People** (*Detect* or 2 to 10). Every line is labelled with who said it:

```
# Transcript: planning-meeting.mkv
# Speakers identified automatically: 2 (Speaker 1 = first to speak)

[00:00:00] Speaker 1: Good morning, everyone. Let's start with today's agenda. First item is the delivery schedule.

[00:00:09] Speaker 2: The sign-up screen is ready for testing, we just need to check it with the support team.
```

- **No account, no token**: speaker separation uses [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) with the [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0) segmentation model (MIT) and the [WeSpeaker ResNet34](https://github.com/wenet-e2e/wespeaker) voice embedding (Apache-2.0), all in ONNX: no PyTorch, ~33 MB of models downloaded once.
- **How it works**: the audio is decoded once; Whisper transcribes with per-word timestamps while, in parallel, diarization finds out who speaks when. Each sentence goes to the speaker that overlaps its words the most.
- **Performance**: on a GTX 1650, a 52-minute meeting was done in 12 minutes (speaker separation runs on the CPU while transcription runs on the GPU).
- **Limitations**: the program doesn't know people's names (Speaker 1 is whoever spoke first); overlapping speech and very short interjections ("yeah", "ok") may go to the wrong speaker; system sounds (spoken alerts) may become a speaker of their own. Giving the number of people improves separation.

To use it: in the `identificacao-de-falantes` folder, run `instalar.bat` and then `iniciar.bat` (or `py transcrever.py "C:\folder" --pessoas 3`).

## Highlights

- **Privacy**: uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (OpenAI's Whisper reimplemented on CTranslate2) right on your machine.
- **GPU with automatic fallback**: checks for an NVIDIA GPU and the CUDA libraries, confirms with a real test run (`large-v3-turbo` model) and, if anything fails, falls back to the CPU (`medium` model) on its own.
- **English and Portuguese interface**: follows the Windows language and can be switched live from the selector in the corner; the choice is remembered.
- **Simple interface** built with Tkinter: pick a folder, filter by name, sort by name or modified date, tick the files, see the total size selected, follow the progress and cancel at any time. Transcription runs on a background thread, so the window never freezes.
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
| Translated passages (e.g. an English meeting coming out in Portuguese) | The language was fixed to the wrong one. Use **Automatic** and transcribe again. |
| "GPU unavailable" in the log | Expected on computers without an NVIDIA card: the program uses the CPU. If you have NVIDIA, use the "NVIDIA" download (or install `requirements-gpu.txt`) and check the driver (`nvidia-smi`, must be 528+). |
| `TypeError: open() got an unexpected keyword argument 'metadata_errors'` | PyAV is too new: `py -m pip install --only-binary=:all: "av<15"` |
| `python` opens the Microsoft Store | Use `py` instead of `python`, or turn off the shortcut in *Settings → Apps → Advanced app settings → App execution aliases* |

## Project structure

```
meet-transcript/
├── .github/release.md             # release notes (PT/EN), updated for each version
├── .github/workflows/release.yml  # builds and publishes the executables
├── identificacao-de-falantes/     # same layout + falantes.py (who speaks when)
└── transcricao-simples/
    ├── app.py                     # graphical interface (Tkinter)
    ├── transcrever.py             # transcription logic + command line
    ├── textos.py                  # interface strings in Portuguese and English
    ├── meet_transcript.spec       # PyInstaller recipe
    ├── LEIA-ME.txt / README.txt   # quick guide shipped inside the .zip (PT/EN)
    ├── instalar.bat / iniciar.bat
    ├── requirements.txt
    └── requirements-gpu.txt       # optional CUDA
```
