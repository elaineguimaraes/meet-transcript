**Português** · [English below](#english)

## Novidades

- **Áudios do WhatsApp**: mensagens de voz (`.ogg` e `.opus`) agora aparecem na lista e são transcritas como qualquer gravação. Útil quando o cliente complementa a reunião mandando áudio.
- **Juntar tudo em um único .txt**: marque essa opção para ter as transcrições de vários arquivos em um só `.txt`, uma depois da outra, na ordem da lista, cada uma com um título com o nome e a data do arquivo. Desmarcada, cada arquivo continua ganhando seu próprio `.txt` e `.srt`.
- **Data de modificação** de cada arquivo na lista (coluna **Modificado em**).
- **Ordenar** clicando no título **Arquivo** ou **Modificado em** (outro clique inverte a ordem). A transcrição segue a ordem da lista.
- **Lembra a última pasta**: o programa já abre na pasta usada da última vez. Na primeira vez, **Escolher...** abre no `C:\`.

## Download para Windows

| Arquivo | Para quem |
|---|---|
| **MeetTranscript-Windows-NVIDIA.zip** | Computadores com placa de vídeo NVIDIA (bem mais rápido) |
| **MeetTranscript-Windows.zip** | Qualquer computador (usa o processador) |

Não precisa instalar o Python. Extraia o .zip e abra **Meet Transcript.exe**.

- Na primeira vez, o Windows pode mostrar "O Windows protegeu o computador": clique em **Mais informações → Executar assim mesmo** (o programa não tem assinatura digital paga).
- Na primeira transcrição o modelo (~1,5 GB) é baixado uma única vez; depois funciona offline.

A versão com **identificação de quem fala** (Voz 1, Voz 2…) está em teste e, por enquanto, roda só pelo código-fonte: veja a pasta [`identificacao-de-falantes`](https://github.com/elaineguimaraes/meet-transcript/tree/main/identificacao-de-falantes).

---

<a id="english"></a>

## What's new

- **WhatsApp voice messages**: `.ogg` and `.opus` audios now show up in the list and are transcribed like any recording. Handy when a client follows up on a meeting with voice messages.
- **Combine into a single .txt**: tick this option to get the transcripts of several files in one `.txt`, one after the other, in list order, each under a heading with the file's name and date. Unticked, each file still gets its own `.txt` and `.srt`.
- **Last modified date** of each file in the list (**Modified** column).
- **Sorting** by clicking the **File** or **Modified** header (click again to reverse). Files are transcribed in list order.
- **Remembers the last folder**: the program opens in the folder you used last time. On first use, **Browse...** opens at `C:\`.

## Download for Windows

| File | For |
|---|---|
| **MeetTranscript-Windows-NVIDIA.zip** | Computers with an NVIDIA graphics card (much faster) |
| **MeetTranscript-Windows.zip** | Any computer (runs on the CPU) |

No Python needed. Extract the .zip and open **Meet Transcript.exe**.

- The first time, Windows may show "Windows protected your PC": click **More info → Run anyway** (the program has no paid code-signing certificate).
- On the first transcription, the model (~1.5 GB) is downloaded once; after that it works offline.

The version with **speaker identification** (Speaker 1, Speaker 2…) is in testing and, for now, runs from source only: see the [`identificacao-de-falantes`](https://github.com/elaineguimaraes/meet-transcript/tree/main/identificacao-de-falantes) folder.
