# Meet Transcript

**Português** | [English](README.en.md)

Transcrição automática de gravações de reunião feitas no **OBS Studio** (ou qualquer vídeo/áudio), rodando **100% local**: nenhum áudio sai do seu computador e não há custo de API.

Basta escolher a pasta com as gravações e marcar quais arquivos transcrever (ou todos). Para cada um são gerados um `.txt` com marcação de tempo e uma legenda `.srt`.

**Formatos aceitos:** MKV, MP4, MOV, FLV, WEBM (vídeo) e M4A, MP3, WAV (áudio).

**Idioma:** detectado automaticamente a cada trecho, então reuniões em inglês, português ou misturando os dois saem no idioma em que foram faladas. Também dá para fixar o idioma.

```
# Transcrição: reuniao-planejamento.mkv

[00:00:00] Bom dia, pessoal. Vamos começar pela pauta de hoje.
[00:00:04] Primeiro item é o cronograma da entrega.
[00:00:07] A tela de cadastro já está pronta para teste,
[00:00:10] falta só validar com o time de suporte.
```

## ⬇️ Download para Windows (sem instalar nada)

Na página da **[última versão](https://github.com/elaineguimaraes/meet-transcript/releases/latest)**, baixe:

| Arquivo | Para quem |
|---|---|
| `MeetTranscript-Windows-NVIDIA.zip` | Computadores com placa de vídeo NVIDIA (bem mais rápido) |
| `MeetTranscript-Windows.zip` | Qualquer computador (usa o processador) |

Extraia o `.zip` e dê dois cliques em **`Meet Transcript.exe`**. Não precisa de Python.

- Na primeira vez, o Windows pode mostrar *"O Windows protegeu o computador"*: clique em **Mais informações → Executar assim mesmo**. O aviso aparece porque o programa não tem assinatura digital paga.
- Na primeira transcrição, o modelo (~1,5 GB) é baixado uma única vez. Depois funciona offline.

## Como usar

1. Clique em **Escolher...** e selecione a pasta com as gravações.
2. Clique nos arquivos para marcá-los (tudo começa desmarcado). Use **Filtrar por nome** para achar um arquivo; os botões **Marcar todos** / **Desmarcar todos** / **Marcar pendentes** agem sobre os arquivos filtrados. Marcar um arquivo já transcrito faz ele ser refeito.
3. Em **Idioma**, deixe **Automático** ou fixe o idioma da reunião. Atenção: fixar o idioma errado faz o modelo *traduzir* a fala.
4. Clique em **Transcrever**. **Cancelar** (ou fechar a janela) interrompe: os arquivos concluídos ficam salvos e o que estava em andamento é descartado.

## Versões

| Pasta | O que faz | Status |
|---|---|---|
| [`transcricao-simples/`](transcricao-simples/) | Transcreve as reuniões, sem separar quem fala | ✅ disponível |
| `identificacao-de-falantes/` | Transcrição com interlocutores separados (Voz 1, Voz 2…) | 🚧 em desenvolvimento |

## Destaques

- **Privacidade**: usa o [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (Whisper da OpenAI reimplementado em CTranslate2) direto na máquina.
- **GPU com fallback automático**: confere se há GPU NVIDIA e bibliotecas CUDA, valida com um teste real (modelo `large-v3-turbo`) e, se algo falhar, cai sozinho para a CPU (modelo `medium`).
- **Interface simples** em Tkinter: escolher a pasta, filtrar por nome, marcar os arquivos, ver o tamanho total selecionado, acompanhar o progresso e cancelar a qualquer momento. A transcrição roda em uma thread separada, então a janela não trava.
- **Retomável**: a lista mostra o que já foi transcrito. A saída é gravada em `.parcial` e só é renomeada no final, então uma execução interrompida nunca deixa uma transcrição pela metade passando por pronta.
- **Rápido**: filtro de voz (VAD) descarta silêncio. Numa GTX 1650 (4 GB), ~2 h de reunião foram transcritas em ~13 min.
- **Release automatizada**: a cada tag `v*`, o [GitHub Actions](.github/workflows/release.yml) gera os executáveis com PyInstaller (versões CPU e NVIDIA), testa e publica a Release.

## Rodar a partir do código-fonte

Requisitos: [Python](https://www.python.org/downloads/) 3.9 a 3.13. Opcional: GPU NVIDIA com 4 GB+ e driver 528 ou mais novo. Não é preciso instalar o ffmpeg: o áudio é lido direto do vídeo.

1. Clone o projeto:
   ```
   git clone https://github.com/elaineguimaraes/meet-transcript.git
   ```
2. Na pasta `transcricao-simples`, dê dois cliques em **`instalar.bat`**. Ele instala as dependências e, se encontrar uma GPU NVIDIA, também o suporte a CUDA.
3. Dê dois cliques em **`iniciar.bat`**.

O código também roda em Linux/macOS (`python app.py`).

### Pela linha de comando

```
cd transcricao-simples
py -m pip install -r requirements.txt
py -m pip install -r requirements-gpu.txt   # opcional, só com GPU NVIDIA
py transcrever.py "C:\caminho\das\gravacoes"
py transcrever.py "C:\caminho\das\gravacoes" --idioma en   # fixa o idioma
```

No executável, o equivalente é `meet-transcript-cli.exe "C:\caminho\das\gravacoes"`.

### Gerar o executável

```
cd transcricao-simples
py -m pip install pyinstaller
py -m PyInstaller meet_transcript.spec                 # versão CPU
set MT_VARIANTE=nvidia && py -m PyInstaller meet_transcript.spec   # versão NVIDIA
```

### Ajustes

Modelo, idioma padrão e formatos aceitos ficam no topo de [`transcrever.py`](transcricao-simples/transcrever.py) (`MODELO_GPU`, `MODELO_CPU`, `IDIOMA`, `EXTENSOES`).

## Problemas comuns

| Sintoma | Solução |
|---|---|
| Trechos traduzidos (ex.: reunião em inglês saindo em português) | O idioma foi fixado errado. Use **Automático** e transcreva de novo. |
| "GPU indisponível" no log | Normal em computadores sem placa NVIDIA: o programa usa o processador. Se você tem NVIDIA, use o download "NVIDIA" (ou instale o `requirements-gpu.txt`) e confira o driver (`nvidia-smi`, precisa ser 528+). |
| `TypeError: open() got an unexpected keyword argument 'metadata_errors'` | PyAV novo demais: `py -m pip install --only-binary=:all: "av<15"` |
| `python` abre a Microsoft Store | Use `py` no lugar de `python`, ou desative o atalho em *Configurações → Aplicativos → Aliases de execução do aplicativo* |

## Estrutura

```
meet-transcript/
├── .github/workflows/release.yml  # gera e publica os executáveis
└── transcricao-simples/
    ├── app.py                     # interface gráfica (Tkinter)
    ├── transcrever.py             # lógica de transcrição + linha de comando
    ├── meet_transcript.spec       # receita do PyInstaller
    ├── LEIA-ME.txt                # guia rápido que vai dentro do .zip
    ├── instalar.bat / iniciar.bat
    ├── requirements.txt
    └── requirements-gpu.txt       # CUDA opcional
```
