# Meet Transcript

**Português** | [English](README.en.md)

Transcrição automática de gravações de reunião feitas no **OBS Studio**, de **mensagens de voz do WhatsApp** ou de qualquer vídeo/áudio, rodando **100% local**: nenhum áudio sai do seu computador e não há custo de API.

Basta escolher a pasta com as gravações e marcar quais arquivos transcrever (ou todos). Para cada um é gerado um `.txt` com marcação de tempo, na subpasta `transcrições` (dentro da pasta das gravações).

**Formatos aceitos:** MKV, MP4, MOV, FLV, WEBM (vídeo) e M4A, MP3, WAV, OGG, OPUS (áudio, inclusive mensagens de voz do WhatsApp).

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

1. Clique em **Escolher...** e selecione a pasta com as gravações. Na próxima vez, o programa já abre nessa pasta.
2. Clique nos arquivos para marcá-los (tudo começa desmarcado). A lista mostra a data da última modificação de cada arquivo; a lista começa pelos mais recentes; clique no título **Arquivo** ou **Modificado em** para mudar a ordem (outro clique inverte). Use **Filtrar por nome** para achar um arquivo; os botões **Marcar todos** / **Desmarcar todos** / **Marcar pendentes** agem sobre os arquivos filtrados. Marcar um arquivo já transcrito faz ele ser refeito.
3. Para ter tudo em um arquivo só, marque **Juntar tudo em um único .txt**: as transcrições saem uma depois da outra, na ordem da lista, em `Transcrição única <data e hora>.txt`. Desmarcado, cada arquivo ganha seu próprio `.txt`.
4. Em **Idioma da fala**, deixe **Automático** ou fixe o idioma da reunião. Atenção: fixar o idioma errado faz o modelo *traduzir* a fala.
5. Clique em **Transcrever**. **Cancelar** (ou fechar a janela) interrompe: os arquivos concluídos ficam salvos (no `.txt` único, se essa opção estiver marcada) e o que estava em andamento é descartado.

## Áudios do WhatsApp

Quando o cliente complementa a reunião mandando áudio no WhatsApp, dá para transcrever esses áudios do mesmo jeito:

1. Baixe os áudios para uma pasta (no WhatsApp Web ou Desktop: menu da mensagem → **Baixar**). Eles vêm como `.ogg` (ou `.opus`, se exportados do celular).
2. Escolha essa pasta no programa, ordene por **Arquivo**, marque os áudios e clique em **Transcrever**. Cada áudio ganha seu próprio `.txt` ou, com **Juntar tudo em um único .txt** marcado, todos vão para um arquivo só, cada um com um título:

```
# Transcrição única: 2 arquivo(s)

## WhatsApp Ptt 2026-11-04 at 10.17.56.ogg (modificado em 04/11/2026 10:18)

[00:00:00] Oi, bom dia! Dei uma validada nos documentos, estão todos na pasta.

## WhatsApp Ptt 2026-11-04 at 10.20.06.ogg (modificado em 04/11/2026 10:21)

[00:00:00] Vou tentar te explicar aqui o fluxo de aprovação.
```

Dica: o nome do arquivo baixado já traz o horário de envio (`WhatsApp Ptt 2026-11-04 at 10.17.56.ogg`), então ordenar por **Arquivo** coloca as mensagens em ordem cronológica. A coluna **Modificado em** mostra quando o arquivo foi salvo no computador, que pode ser bem depois do envio.

## Versões

| Pasta | O que faz | Status |
|---|---|---|
| [`transcricao-simples/`](transcricao-simples/) | Transcreve as reuniões, sem separar quem fala | ✅ disponível |
| [`identificacao-de-falantes/`](identificacao-de-falantes/) | Transcrição com interlocutores separados (Voz 1, Voz 2…) | 🧪 em teste (pelo código-fonte) |

### Identificação de falantes (em teste)

Mesma interface, com um seletor a mais: **Pessoas** (*Descobrir* ou de 2 a 10). Cada fala sai marcada com quem falou:

```
# Transcrição: reuniao-planejamento.mkv
# Vozes identificadas automaticamente: 2 (Voz 1 = quem falou primeiro)

[00:00:00] Voz 1: Bom dia, pessoal. Vamos começar pela pauta de hoje. Primeiro item é o cronograma da entrega.

[00:00:09] Voz 2: A tela de cadastro já está pronta para teste, falta só validar com o time de suporte.
```

- **Sem conta e sem token**: a separação de vozes usa o [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) com o modelo de segmentação [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0) (MIT) e a "impressão digital de voz" [WeSpeaker ResNet34](https://github.com/wenet-e2e/wespeaker) (Apache-2.0), tudo em ONNX: sem PyTorch, ~33 MB de modelos baixados uma vez.
- **Como funciona**: o áudio é decodificado uma vez; o Whisper transcreve com o tempo de cada palavra enquanto, em paralelo, a diarização descobre quem fala quando. Cada frase fica com a voz que mais se sobrepõe às suas palavras.
- **Desempenho**: numa GTX 1650, uma reunião de 52 min ficou pronta em 12 min (a separação de vozes roda na CPU, ao mesmo tempo que a transcrição na GPU).
- **Limitações**: o programa não sabe o nome das pessoas (Voz 1 é quem falou primeiro); falas sobrepostas e interjeições muito curtas ("é", "tá") podem ir para a voz errada; sons de sistema (alertas falados) podem virar uma voz própria. Informar o número de pessoas melhora a separação.

Para usar: na pasta `identificacao-de-falantes`, rode `instalar.bat` e depois `iniciar.bat` (ou `py transcrever.py "C:\pasta" --pessoas 3`).

## Destaques

- **Privacidade**: usa o [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (Whisper da OpenAI reimplementado em CTranslate2) direto na máquina.
- **GPU com fallback automático**: confere se há GPU NVIDIA e bibliotecas CUDA, valida com um teste real (modelo `large-v3-turbo`) e, se algo falhar, cai sozinho para a CPU (modelo `medium`).
- **Interface em português e inglês**: segue o idioma do Windows e pode ser trocada na hora pelo seletor no canto da janela; a escolha fica salva.
- **Interface simples** em Tkinter: escolher a pasta, filtrar por nome, ordenar por nome ou data de modificação, marcar os arquivos, ver o tamanho total selecionado, acompanhar o progresso e cancelar a qualquer momento. A transcrição roda em uma thread separada, então a janela não trava.
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
├── .github/release.md             # texto da release (PT/EN), atualizado a cada versão
├── .github/workflows/release.yml  # gera e publica os executáveis
├── identificacao-de-falantes/     # mesma estrutura + falantes.py (quem fala quando)
└── transcricao-simples/
    ├── app.py                     # interface gráfica (Tkinter)
    ├── transcrever.py             # lógica de transcrição + linha de comando
    ├── textos.py                  # textos da interface em português e inglês
    ├── meet_transcript.spec       # receita do PyInstaller
    ├── LEIA-ME.txt / README.txt   # guia rápido que vai dentro do .zip (PT/EN)
    ├── instalar.bat / iniciar.bat
    ├── requirements.txt
    └── requirements-gpu.txt       # CUDA opcional
```
