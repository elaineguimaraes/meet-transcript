# Meet Transcript

Transcrição automática de gravações de reunião feitas no **OBS Studio** (ou qualquer vídeo/áudio), rodando **100% local**: nenhum áudio sai do seu computador e não há custo de API.

Basta escolher a pasta com as gravações. Para cada vídeo são gerados um `.txt` com marcação de tempo e uma legenda `.srt`.

```
# Transcrição: reuniao-planejamento.mkv

[00:00:00] Bom dia, pessoal. Vamos começar pela pauta de hoje.
[00:00:04] Primeiro item é o cronograma da entrega.
[00:00:07] A tela de cadastro já está pronta para teste,
[00:00:10] falta só validar com o time de suporte.
```

## Versões

| Pasta | O que faz | Status |
|---|---|---|
| [`transcricao-simples/`](transcricao-simples/) | Transcreve as reuniões, sem separar quem fala | ✅ disponível |
| `identificacao-de-falantes/` | Transcrição com interlocutores separados (Voz 1, Voz 2…) | 🚧 em desenvolvimento |

## Destaques

- **Privacidade**: usa o [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (Whisper da OpenAI reimplementado em CTranslate2) direto na máquina.
- **GPU com fallback automático**: tenta a GPU NVIDIA (modelo `large-v3-turbo`), valida com um teste real e, se o CUDA falhar, cai sozinho para a CPU (modelo `medium`).
- **Interface simples** em Tkinter: escolher pasta, acompanhar o progresso, abrir o resultado. A transcrição roda em uma thread separada, então a janela não trava.
- **Retomável**: arquivos já transcritos são pulados. A saída é gravada em `.parcial` e só é renomeada no final, então uma execução interrompida nunca deixa uma transcrição pela metade passando por pronta.
- **Rápido**: filtro de voz (VAD) descarta silêncio. Numa GTX 1650 (4 GB), ~2 h de reunião foram transcritas em ~13 min.

## Requisitos

- Windows 10/11 (o código também roda em Linux/macOS pela linha de comando ou pela interface)
- [Python](https://www.python.org/downloads/) 3.9 a 3.13
- Opcional: GPU NVIDIA com 4 GB+ e driver 528 ou mais novo. Sem GPU funciona na CPU, só que mais devagar.

Não é preciso instalar o ffmpeg: o áudio é lido direto do vídeo.

## Como usar

1. Baixe o projeto (**Code → Download ZIP**) ou clone:
   ```
   git clone https://github.com/elaineguimaraes/meet-transcript.git
   ```
2. Na pasta `transcricao-simples`, dê dois cliques em **`instalar.bat`**. Ele instala as dependências e, se encontrar uma GPU NVIDIA, também o suporte a CUDA.
3. Dê dois cliques em **`iniciar.bat`**, escolha a pasta com as gravações e clique em **Transcrever**.

Na primeira execução o modelo é baixado (~1,5 GB), uma única vez.

### Pela linha de comando

```
cd transcricao-simples
py -m pip install -r requirements.txt
py -m pip install -r requirements-gpu.txt   # opcional, só com GPU NVIDIA
py transcrever.py "C:\caminho\das\gravacoes"
```

### Ajustes

Modelo, idioma e formatos aceitos ficam no topo de [`transcrever.py`](transcricao-simples/transcrever.py) (`MODELO_GPU`, `MODELO_CPU`, `IDIOMA`, `EXTENSOES`).

## Problemas comuns

| Sintoma | Solução |
|---|---|
| `TypeError: open() got an unexpected keyword argument 'metadata_errors'` | PyAV novo demais: `py -m pip install --only-binary=:all: "av<15"` |
| "GPU indisponível" no log | Confira o driver NVIDIA (`nvidia-smi`, precisa ser 528+) e se o `requirements-gpu.txt` foi instalado. O programa segue na CPU mesmo assim. |
| `python` abre a Microsoft Store | Use `py` no lugar de `python`, ou desative o atalho em *Configurações → Aplicativos → Aliases de execução do aplicativo* |

## Estrutura

```
meet-transcript/
└── transcricao-simples/
    ├── app.py                 # interface gráfica (Tkinter)
    ├── transcrever.py         # lógica de transcrição + linha de comando
    ├── instalar.bat / iniciar.bat
    ├── requirements.txt
    └── requirements-gpu.txt   # CUDA opcional
```

---

**English:** Offline meeting transcription for OBS Studio recordings, built on faster-whisper. Pick a folder in a small Tkinter GUI and every video gets a timestamped `.txt` and an `.srt` subtitle. Runs on an NVIDIA GPU when available, with automatic CPU fallback. Tuned for Portuguese; change `IDIOMA` in `transcrever.py` for other languages.
