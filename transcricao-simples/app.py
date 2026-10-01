"""Interface gráfica: escolha a pasta, marque as gravações e clique em Transcrever."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

CAIXA = {True: "☑", False: "☐"}


def tamanho_legivel(arquivo: Path) -> str:
    mb = arquivo.stat().st_size / 1024**2
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb:.0f} MB" if mb >= 1 else "< 1 MB"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Meet Transcript")
        self.minsize(720, 620)

        self.fila: queue.Queue = queue.Queue()  # mensagens da thread de trabalho para a tela
        self.transcritor = None                 # módulo transcrever, importado em segundo plano
        self.rodando = False
        self.pasta = tk.StringVar()
        self.videos: list[Path] = []
        self.marcados: set[str] = set()         # iids (caminho do arquivo) marcados na lista

        self._montar_tela()
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        # Importar o faster-whisper leva alguns segundos; a janela abre antes.
        threading.Thread(target=self._importar_transcritor, daemon=True).start()
        self.after(100, self._processar_fila)

    # ------------------------------------------------------------------ tela

    def _montar_tela(self) -> None:
        # Altura de linha proporcional à fonte, para não cortar texto com escala de tela.
        altura = font.nametofont("TkDefaultFont").metrics("linespace") + 6
        ttk.Style(self).configure("Treeview", rowheight=altura)

        raiz = ttk.Frame(self, padding=12)
        raiz.pack(fill="both", expand=True)
        raiz.columnconfigure(0, weight=1)
        raiz.rowconfigure(3, weight=3)
        raiz.rowconfigure(7, weight=1)

        ttk.Label(raiz, text="Pasta com as gravações:").grid(row=0, column=0, columnspan=2, sticky="w")
        entrada = ttk.Entry(raiz, textvariable=self.pasta)
        entrada.grid(row=1, column=0, sticky="ew", pady=(2, 6))
        entrada.bind("<Return>", lambda _: self._carregar_lista())
        self.botao_escolher = ttk.Button(raiz, text="Escolher...", command=self._escolher_pasta)
        self.botao_escolher.grid(row=1, column=1, padx=(6, 0), pady=(2, 6))
        self.formatos = ttk.Label(raiz, text="", foreground="#666666")
        self.formatos.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 6))

        # Lista de arquivos com caixa de marcar (clique na linha para marcar/desmarcar).
        quadro = ttk.Frame(raiz)
        quadro.grid(row=3, column=0, columnspan=2, sticky="nsew")
        quadro.columnconfigure(0, weight=1)
        quadro.rowconfigure(0, weight=1)
        self.lista = ttk.Treeview(
            quadro, columns=("marca", "nome", "tamanho", "situacao"), show="headings", selectmode="none"
        )
        for coluna, titulo, largura, estica, alinhar in (
            ("marca", "", 36, False, "center"),
            ("nome", "Arquivo", 320, True, "w"),
            ("tamanho", "Tamanho", 80, False, "e"),
            ("situacao", "Situação", 110, False, "w"),
        ):
            self.lista.heading(coluna, text=titulo, anchor=alinhar)
            self.lista.column(coluna, width=largura, minwidth=largura, stretch=estica, anchor=alinhar)
        self.lista.tag_configure("feito", foreground="#7a7a7a")
        self.lista.bind("<Button-1>", self._clicar_lista)
        rolagem = ttk.Scrollbar(quadro, orient="vertical", command=self.lista.yview)
        self.lista.configure(yscrollcommand=rolagem.set)
        self.lista.grid(row=0, column=0, sticky="nsew")
        rolagem.grid(row=0, column=1, sticky="ns")

        selecao = ttk.Frame(raiz)
        selecao.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.botoes_selecao = [
            ttk.Button(selecao, text="Marcar todos", command=lambda: self._marcar("todos")),
            ttk.Button(selecao, text="Desmarcar todos", command=lambda: self._marcar("nenhum")),
            ttk.Button(selecao, text="Só pendentes", command=lambda: self._marcar("pendentes")),
        ]
        for i, botao in enumerate(self.botoes_selecao):
            botao.pack(side="left", padx=(0 if i == 0 else 6, 0))
        self.contagem = ttk.Label(selecao, text="")
        self.contagem.pack(side="left", padx=(12, 0))

        acoes = ttk.Frame(raiz)
        acoes.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 4))
        self.botao_transcrever = ttk.Button(
            acoes, text="Transcrever", command=self._iniciar, state="disabled"
        )
        self.botao_transcrever.pack(side="left")
        self.botao_abrir = ttk.Button(acoes, text="Abrir pasta", command=self._abrir_pasta)
        self.botao_abrir.pack(side="left", padx=(6, 0))
        self.status = ttk.Label(acoes, text="Preparando...")
        self.status.pack(side="left", padx=(12, 0))

        self.barra = ttk.Progressbar(raiz, maximum=100)
        self.barra.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        self.log = ScrolledText(raiz, height=7, state="disabled", wrap="word")
        self.log.grid(row=7, column=0, columnspan=2, sticky="nsew")

    def _escrever(self, texto: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", texto + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    # ------------------------------------------------------- lista de arquivos

    def _carregar_lista(self) -> None:
        """(Re)lê a pasta. Pendentes vêm marcados; os já transcritos, desmarcados."""
        self.lista.delete(*self.lista.get_children())
        self.videos, self.marcados = [], set()

        texto = self.pasta.get().strip().strip('"')
        pasta = Path(texto)
        if self.transcritor and texto and pasta.is_dir():
            self.videos = self.transcritor.listar_videos(pasta)
            for video in self.videos:
                feito = video.with_suffix(".txt").exists()
                iid = str(video)
                self.lista.insert(
                    "", "end", iid=iid, tags=("feito",) if feito else (),
                    values=(CAIXA[not feito], video.name, tamanho_legivel(video),
                            "já transcrito" if feito else "pendente"),
                )
                if not feito:
                    self.marcados.add(iid)
            if not self.videos:
                self._escrever(f"Nenhum vídeo ou áudio em {pasta}")
        self._atualizar_contagem()

    def _definir_marca(self, iid: str, marcado: bool) -> None:
        if marcado:
            self.marcados.add(iid)
        else:
            self.marcados.discard(iid)
        self.lista.set(iid, "marca", CAIXA[marcado])

    def _clicar_lista(self, evento: tk.Event) -> None:
        iid = self.lista.identify_row(evento.y)
        if self.rodando or not iid or self.lista.identify_region(evento.x, evento.y) != "cell":
            return
        self._definir_marca(iid, iid not in self.marcados)
        self._atualizar_contagem()

    def _marcar(self, quais: str) -> None:
        for video in self.videos:
            pendente = not video.with_suffix(".txt").exists()
            self._definir_marca(str(video), quais == "todos" or (quais == "pendentes" and pendente))
        self._atualizar_contagem()

    def _selecionados(self) -> list[Path]:
        return [v for v in self.videos if str(v) in self.marcados]

    def _atualizar_contagem(self) -> None:
        n = len(self.marcados)
        self.contagem.configure(
            text=f"{n} de {len(self.videos)} selecionado(s)" if self.videos else ""
        )
        self.botao_transcrever.configure(
            text=f"Transcrever ({n})" if n else "Transcrever",
            state="normal" if n and self.transcritor and not self.rodando else "disabled",
        )

    # ----------------------------------------------------------------- ações

    def _escolher_pasta(self) -> None:
        escolhida = filedialog.askdirectory(title="Escolha a pasta com as gravações")
        if escolhida:
            self.pasta.set(str(Path(escolhida)))
            self._carregar_lista()

    def _iniciar(self) -> None:
        videos = self._selecionados()
        if not videos:
            return
        refazer = [v for v in videos if v.with_suffix(".txt").exists()]
        if refazer and not messagebox.askokcancel(
            "Meet Transcript",
            f"{len(refazer)} arquivo(s) marcado(s) já têm transcrição e serão refeitos "
            "(o .txt e o .srt atuais serão substituídos). Continuar?",
        ):
            return

        self.rodando = True
        for botao in (self.botao_escolher, *self.botoes_selecao):
            botao.configure(state="disabled")
        self._atualizar_contagem()
        self.barra["value"] = 0
        self.status.configure(text="Transcrevendo...")
        threading.Thread(target=self._trabalhar, args=(videos,), daemon=True).start()

    def _abrir_pasta(self) -> None:
        pasta = self.pasta.get().strip().strip('"')
        if not pasta or not Path(pasta).is_dir():
            return
        if os.name == "nt":
            os.startfile(pasta)
        else:
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", pasta])

    def _fechar(self) -> None:
        if self.rodando and not messagebox.askokcancel(
            "Meet Transcript", "A transcrição em andamento será interrompida. Sair mesmo assim?"
        ):
            return
        self.destroy()

    # --------------------------------------------- trabalho em segundo plano

    def _importar_transcritor(self) -> None:
        try:
            import transcrever

            self.fila.put(("modulo", transcrever))
        except Exception as erro:  # noqa: BLE001
            self.fila.put(("erro_modulo", f"{erro.__class__.__name__}: {erro}"))

    def _trabalhar(self, videos: list[Path]) -> None:
        try:
            n = self.transcritor.transcrever_arquivos(
                videos,
                log=lambda texto: self.fila.put(("log", texto)),
                progresso=lambda i, total, fracao: self.fila.put(("progresso", (i, total, fracao))),
            )
            self.fila.put(("fim", n))
        except Exception as erro:  # noqa: BLE001
            self.fila.put(("erro", f"{erro.__class__.__name__}: {erro}"))

    def _processar_fila(self) -> None:
        """Roda na thread da tela: o tkinter não pode ser mexido por outras threads."""
        try:
            while True:
                tipo, dado = self.fila.get_nowait()
                if tipo == "log":
                    self._escrever(dado)
                elif tipo == "progresso":
                    i, total, fracao = dado
                    self.barra["value"] = (i + fracao) / total * 100
                    self.status.configure(text=f"Arquivo {i + 1} de {total}: {fracao:.0%}")
                elif tipo == "modulo":
                    self.transcritor = dado
                    self.status.configure(text="Pronto.")
                    formatos = ", ".join(e.lstrip(".").upper() for e in sorted(dado.EXTENSOES))
                    self.formatos.configure(text=f"Formatos aceitos: {formatos}")
                    self._carregar_lista()  # caso a pasta tenha sido escolhida antes
                elif tipo == "erro_modulo":
                    self.status.configure(text="Dependências não instaladas.")
                    self._escrever(f"Erro ao carregar o faster-whisper: {dado}")
                    self._escrever("Rode instalar.bat (ou: py -m pip install -r requirements.txt).")
                elif tipo in ("fim", "erro"):
                    self._terminar(tipo, dado)
        except queue.Empty:
            pass
        self.after(100, self._processar_fila)

    def _terminar(self, tipo: str, dado) -> None:
        self.rodando = False
        for botao in (self.botao_escolher, *self.botoes_selecao):
            botao.configure(state="normal")
        if tipo == "fim":
            self.barra["value"] = 100
            self.status.configure(text=f"Concluído: {dado} arquivo(s) transcrito(s).")
        else:
            self.status.configure(text="Erro.")
            self._escrever(f"ERRO: {dado}")
            messagebox.showerror("Meet Transcript", dado)
        self._carregar_lista()  # atualiza a situação de cada arquivo


def main() -> None:
    if os.name == "nt":
        try:  # texto nítido em telas com escala (125%, 150%...)
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa: BLE001
            pass
    App().mainloop()


if __name__ == "__main__":
    main()
