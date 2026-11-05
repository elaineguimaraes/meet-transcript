MEET TRANSCRIPT - meeting transcription with speaker identification
===================================================================

HOW TO USE
1. Double-click "Meet Transcript.exe".
   (The interface follows your Windows language; switch between English and
   Português in the top-right corner.)
2. Click "Browse..." and select the folder with your recordings.
3. Click the files you want to transcribe (or "Select all").
   Click the "File" or "Modified" header to sort the list.
   Tick "Combine into a single .txt" to get every transcript in one
   file (handy for several WhatsApp voice messages).
4. In "People", keep "Detect" or pick how many people speak in the
   meeting (giving the number makes speaker separation more accurate).
5. Click "Transcribe".

Next to each video you get:
  - a .txt with each line, its timestamp and who said it:
        [00:00:25] Speaker 2: Got it. Go ahead.
  - a .srt subtitle file, to watch along with the video

Speakers are numbered in order of appearance (Speaker 1 = first to speak).
The program doesn't know people's names: to turn "Speaker 1" into a name,
use "Replace" in Notepad.

Supported formats: MKV, MP4, MOV, FLV, WEBM, M4A, MP3, WAV, OGG and OPUS (WhatsApp voice messages).

Spoken language: keep it on "Automatic" (detects the language, including
meetings that mix languages). If you fix a language, pick the right one:
with the wrong language the program translates the speech instead of
transcribing it.

FIRST RUN
- Windows may show "Windows protected your PC".
  Click "More info" and then "Run anyway".
  (The warning appears because the program has no paid code-signing certificate.)
- The program downloads the transcription model (~1.5 GB), only once.
  You need an internet connection for that. After that it works offline.

PRIVACY
Everything runs on your computer. No audio is sent to the internet.

TIPS
- Don't move "Meet Transcript.exe" out of this folder: it needs the
  "_internal" folder next to it. For a desktop shortcut, right-click the .exe >
  "Send to" > "Desktop (create shortcut)".
- If you have an NVIDIA graphics card, use the "NVIDIA" download: it is much faster.
- Advanced: meet-transcript-cli.exe "C:\folder" transcribes from the command line.

Source code and help: https://github.com/elaineguimaraes/meet-transcript
