"""Textos da interface e das mensagens, em português e inglês.

O idioma inicial segue o do sistema (português se o Windows estiver em português;
inglês nos demais casos) e pode ser trocado com definir_idioma().
"""

from __future__ import annotations

import locale
import os

TEXTOS: dict[str, dict[str, str]] = {
    "pt": {
        # tela
        "pasta": "Pasta com as gravações:",
        "escolher": "Escolher...",
        "escolher_titulo": "Escolha a pasta com as gravações",
        "formatos": "Formatos aceitos: {lista}",
        "filtrar": "Filtrar por nome:",
        "limpar": "Limpar",
        "col_arquivo": "Arquivo",
        "col_tamanho": "Tamanho",
        "col_situacao": "Situação",
        "feito": "já transcrito",
        "pendente": "pendente",
        "marcar_todos": "Marcar todos",
        "desmarcar_todos": "Desmarcar todos",
        "marcar_pendentes": "Marcar pendentes",
        "contagem": "{n} de {total} selecionado(s)",
        "no_filtro": "{n} no filtro",
        "idioma_fala": "Idioma da fala:",
        "auto": "Automático",
        "pt": "Português",
        "en": "Inglês",
        "es": "Espanhol",
        "transcrever": "Transcrever",
        "transcrever_n": "Transcrever ({n})",
        "cancelar": "Cancelar",
        "abrir_pasta": "Abrir pasta",
        # situação
        "preparando": "Preparando...",
        "pronto": "Pronto.",
        "transcrevendo": "Transcrevendo...",
        "cancelando": "Cancelando...",
        "progresso": "Arquivo {i} de {total}: {pct}",
        "fim": "Concluído: {n} arquivo(s) transcrito(s).",
        "cancelado": "Cancelado.",
        "erro": "Erro.",
        "sem_dependencias": "Dependências não instaladas.",
        # avisos
        "confirma_refazer": "{n} arquivo(s) marcado(s) já têm transcrição e serão refeitos "
                            "(o .txt e o .srt atuais serão substituídos). Continuar?",
        "confirma_sair": "A transcrição será cancelada. Os arquivos já concluídos ficam salvos; "
                         "o que está em andamento é descartado. Sair mesmo assim?",
        # log
        "log_cancelado": "Cancelado. Os arquivos concluídos foram mantidos; o que estava em andamento foi descartado.",
        "log_erro_modulo": "Erro ao carregar o faster-whisper: {erro}",
        "log_dica_instalar": "Rode instalar.bat (ou: py -m pip install -r requirements.txt).",
        "log_erro": "ERRO: {erro}",
        "nenhum_video": "Nenhum vídeo ou áudio em {pasta}",
        "pulando": "[pulando] {nome}: já existe {txt}",
        "nada_a_fazer": "Nada a fazer: todos os arquivos já têm transcrição.",
        "carregando_gpu": "Carregando {modelo} na GPU (na primeira vez baixa ~1,6 GB)...",
        "gpu_ok": "GPU ok.",
        "gpu_indisponivel": "GPU indisponível ({erro})",
        "sem_gpu": "nenhuma GPU NVIDIA encontrada",
        "sem_dll": "{dll} não encontrada; para usar a GPU, instale o suporte a CUDA",
        "carregando_cpu": "Carregando {modelo} na CPU (na primeira vez baixa ~1,5 GB)...",
        "duracao": "    duração {duracao}, idioma: {idioma}, transcrevendo...",
        "idioma_auto": "automático, começa em {codigo}",
        "arquivo_pronto": "    pronto em {tempo} -> {arquivo}",
        "concluido": "Concluído.",
        "pasta_nao_encontrada": "Pasta não encontrada: {pasta}",
        # arquivo gerado
        "cabecalho": "# Transcrição: {nome}",
        # linha de comando
        "uso": "Uso:\n"
               "    {prog} \"C:\\pasta\\das\\gravacoes\"\n"
               "    {prog} \"C:\\pasta\\das\\gravacoes\" --idioma en\n\n"
               "Sem --idioma, o idioma da fala é detectado automaticamente a cada trecho.",
    },
    "en": {
        "pasta": "Recordings folder:",
        "escolher": "Browse...",
        "escolher_titulo": "Choose the folder with the recordings",
        "formatos": "Supported formats: {lista}",
        "filtrar": "Filter by name:",
        "limpar": "Clear",
        "col_arquivo": "File",
        "col_tamanho": "Size",
        "col_situacao": "Status",
        "feito": "transcribed",
        "pendente": "pending",
        "marcar_todos": "Select all",
        "desmarcar_todos": "Select none",
        "marcar_pendentes": "Select pending",
        "contagem": "{n} of {total} selected",
        "no_filtro": "{n} shown",
        "idioma_fala": "Spoken language:",
        "auto": "Automatic",
        "pt": "Portuguese",
        "en": "English",
        "es": "Spanish",
        "transcrever": "Transcribe",
        "transcrever_n": "Transcribe ({n})",
        "cancelar": "Cancel",
        "abrir_pasta": "Open folder",
        "preparando": "Loading...",
        "pronto": "Ready.",
        "transcrevendo": "Transcribing...",
        "cancelando": "Cancelling...",
        "progresso": "File {i} of {total}: {pct}",
        "fim": "Done: {n} file(s) transcribed.",
        "cancelado": "Cancelled.",
        "erro": "Error.",
        "sem_dependencias": "Dependencies not installed.",
        "confirma_refazer": "{n} selected file(s) already have a transcript and will be redone "
                            "(the current .txt and .srt will be replaced). Continue?",
        "confirma_sair": "The transcription will be cancelled. Finished files are kept; "
                         "the one in progress is discarded. Quit anyway?",
        "log_cancelado": "Cancelled. Finished files were kept; the one in progress was discarded.",
        "log_erro_modulo": "Error loading faster-whisper: {erro}",
        "log_dica_instalar": "Run instalar.bat (or: py -m pip install -r requirements.txt).",
        "log_erro": "ERROR: {erro}",
        "nenhum_video": "No video or audio files in {pasta}",
        "pulando": "[skipping] {nome}: {txt} already exists",
        "nada_a_fazer": "Nothing to do: every file already has a transcript.",
        "carregando_gpu": "Loading {modelo} on the GPU (first run downloads ~1.6 GB)...",
        "gpu_ok": "GPU ok.",
        "gpu_indisponivel": "GPU unavailable ({erro})",
        "sem_gpu": "no NVIDIA GPU found",
        "sem_dll": "{dll} not found; install CUDA support to use the GPU",
        "carregando_cpu": "Loading {modelo} on the CPU (first run downloads ~1.5 GB)...",
        "duracao": "    duration {duracao}, language: {idioma}, transcribing...",
        "idioma_auto": "automatic, starts in {codigo}",
        "arquivo_pronto": "    done in {tempo} -> {arquivo}",
        "concluido": "Done.",
        "pasta_nao_encontrada": "Folder not found: {pasta}",
        "cabecalho": "# Transcript: {nome}",
        "uso": "Usage:\n"
               "    {prog} \"C:\\path\\to\\recordings\"\n"
               "    {prog} \"C:\\path\\to\\recordings\" --idioma en\n\n"
               "Without --idioma, the spoken language is detected automatically for each chunk.",
    },
}

NOMES = {"pt": "Português", "en": "English"}  # para o seletor da interface


def idioma_do_sistema() -> str:
    try:
        if os.name == "nt":
            import ctypes

            # LANGID: os 10 bits baixos são o idioma principal; 0x16 = português.
            principal = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
            return "pt" if principal == 0x16 else "en"
        codigo = locale.getlocale()[0] or os.environ.get("LANG", "")
        return "pt" if codigo.lower().startswith("pt") else "en"
    except Exception:  # noqa: BLE001
        return "en"


_atual = idioma_do_sistema()


def definir_idioma(idioma: str) -> None:
    global _atual
    _atual = idioma if idioma in TEXTOS else "en"


def idioma_atual() -> str:
    return _atual


def t(chave: str, **valores) -> str:
    return TEXTOS[_atual][chave].format(**valores)
