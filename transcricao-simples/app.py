"""Interface gráfica: escolha a pasta, marque as gravações e clique em Transcrever."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

CAIXA = {True: "☑", False: "☐"}


def tamanho_legivel(n_bytes: float) -> str:
    mb = n_bytes / 1024**2
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB".replace(".", ",")
    return f"{mb:.0f} MB" if mb >= 1 or n_bytes == 0 else "< 1 MB"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Meet Transcript")
        self.minsize(720, 660)

        self.fila: queue.Queue = queue.Queue()  # mensagens da thread de trabalho para a tela
        self.transcritor = None                 # módulo transcrever, importado em segundo plano
        self.trabalho: threading.Thread | None = None
        self.cancelar = threading.Event()
        self.pasta = tk.StringVar()
        self.filtro = tk.StringVar()
        self.filtro.trace_add("write", lambda *_: self._mostrar_lista())

        # Arquivos da pasta. As chaves dos conjuntos/dicionários são str(caminho),
        # que também é o iid da linha na lista.
        self.videos: list[Path] = []
        self.visiveis: list[Path] = []          # os que passam no filtro
        self.tamanhos: dict[str, int] = {}
        self.feitos: set[str] = set()           # já têm .txt
        self.marcados: set[str] = set()

        self._montar_tela()
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        # Importar o faster-whisper leva alguns segundos; a janela abre antes.
        threading.Thread(target=self._importar_transcritor, daemon=True).start()
        self.after(100, self._processar_fila)

    @property
    def rodando(self) -> bool:
        return self.trabalho is not None and self.trabalho.is_alive()

    # ------------------------------------------------------------------ tela

    def _montar_tela(self) -> None:
        # Altura de linha proporcional à fonte, para não cortar texto com escala de tela.
        altura = font.nametofont("TkDefaultFont").metrics("linespace") + 6
        ttk.Style(self).configure("Treeview", rowheight=altura)

        raiz = ttk.Frame(self, padding=12)
        raiz.pack(fill="both", expand=True)
        raiz.columnconfigure(0, weight=1)
        raiz.rowconfigure(4, weight=3)
        raiz.rowconfigure(8, weight=1)

        ttk.Label(raiz, text="Pasta com as gravações:").grid(row=0, column=0, columnspan=2, sticky="w")
        entrada = ttk.Entry(raiz, textvariable=self.pasta)
        entrada.grid(row=1, column=0, sticky="ew", pady=(2, 2))
        entrada.bind("<Return>", lambda _: self._carregar_lista())
        self.botao_escolher = ttk.Button(raiz, text="Escolher...", command=self._escolher_pasta)
        self.botao_escolher.grid(row=1, column=1, padx=(6, 0), pady=(2, 2))
        self.formatos = ttk.Label(raiz, text="", foreground="#666666")
        self.formatos.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 8))

        busca = ttk.Frame(raiz)
        busca.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        busca.columnconfigure(1, weight=1)
        ttk.Label(busca, text="Filtrar por nome:").grid(row=0, column=0, padx=(0, 6))
        ttk.Entry(busca, textvariable=self.filtro).grid(row=0, column=1, sticky="ew")
        ttk.Button(busca, text="Limpar", command=lambda: self.filtro.set("")).grid(
            row=0, column=2, padx=(6, 0)
        )

        # Lista de arquivos com caixa de marcar (clique na linha para marcar/desmarcar).
        quadro = ttk.Frame(raiz)
        quadro.grid(row=4, column=0, columnspan=2, sticky="nsew")
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
        self.lista.tag_configure("marcado", background="#cfe3ff")
        self.lista.bind("<Button-1>", self._clicar_lista)
        rolagem = ttk.Scrollbar(quadro, orient="vertical", command=self.lista.yview)
        self.lista.configure(yscrollcommand=rolagem.set)
        self.lista.grid(row=0, column=0, sticky="nsew")
        rolagem.grid(row=0, column=1, sticky="ns")

        selecao = ttk.Frame(raiz)
        selecao.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.botoes_selecao = [
            ttk.Button(selecao, text="Marcar todos", command=lambda: self._marcar("todos")),
            ttk.Button(selecao, text="Desmarcar todos", command=lambda: self._marcar("nenhum")),
            ttk.Button(selecao, text="Marcar pendentes", command=lambda: self._marcar("pendentes")),
        ]
        for i, botao in enumerate(self.botoes_selecao):
            botao.pack(side="left", padx=(0 if i == 0 else 6, 0))
        self.contagem = ttk.Label(selecao, text="")
        self.contagem.pack(side="left", padx=(12, 0))

        acoes = ttk.Frame(raiz)
        acoes.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(10, 4))
        self.botao_transcrever = ttk.Button(
            acoes, text="Transcrever", command=self._iniciar, state="disabled"
        )
        self.botao_transcrever.pack(side="left")
        self.botao_cancelar = ttk.Button(
            acoes, text="Cancelar", command=self._pedir_cancelamento, state="disabled"
        )
        self.botao_cancelar.pack(side="left", padx=(6, 0))
        self.botao_abrir = ttk.Button(acoes, text="Abrir pasta", command=self._abrir_pasta)
        self.botao_abrir.pack(side="left", padx=(6, 0))
        self.status = ttk.Label(acoes, text="Preparando...")
        self.status.pack(side="left", padx=(12, 0))

        self.barra = ttk.Progressbar(raiz, maximum=100)
        self.barra.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        self.log = ScrolledText(raiz, height=7, state="disabled", wrap="word")
        self.log.grid(row=8, column=0, columnspan=2, sticky="nsew")

    def _escrever(self, texto: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", texto + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    # ------------------------------------------------------- lista de arquivos

    def _carregar_lista(self) -> None:
        """(Re)lê a pasta. Tudo começa desmarcado."""
        self.videos, self.tamanhos, self.feitos, self.marcados = [], {}, set(), set()

        texto = self.pasta.get().strip().strip('"')
        pasta = Path(texto)
        if self.transcritor and texto and pasta.is_dir():
            self.videos = self.transcritor.listar_videos(pasta)
            for video in self.videos:
                self.tamanhos[str(video)] = video.stat().st_size
                if video.with_suffix(".txt").exists():
                    self.feitos.add(str(video))
            if not self.videos:
                self._escrever(f"Nenhum vídeo ou áudio em {pasta}")
        self._mostrar_lista()

    def _mostrar_lista(self) -> None:
        """Redesenha a lista aplicando o filtro; as marcações são preservadas."""
        self.lista.delete(*self.lista.get_children())
        termo = self.filtro.get().strip().lower()
        self.visiveis = [v for v in self.videos if termo in v.name.lower()]
        for video in self.visiveis:
            iid = str(video)
            feito = iid in self.feitos
            self.lista.insert(
                "", "end", iid=iid, tags=self._tags(iid),
                values=(CAIXA[iid in self.marcados], video.name,
                        tamanho_legivel(self.tamanhos[iid]), "já transcrito" if feito else "pendente"),
            )
        self._atualizar_contagem()

    def _tags(self, iid: str) -> tuple[str, ...]:
        return tuple(t for t, ativo in (("feito", iid in self.feitos), ("marcado", iid in self.marcados)) if ativo)

    def _definir_marca(self, iid: str, marcado: bool) -> None:
        if marcado:
            self.marcados.add(iid)
        else:
            self.marcados.discard(iid)
        if self.lista.exists(iid):
            self.lista.set(iid, "marca", CAIXA[marcado])
            self.lista.item(iid, tags=self._tags(iid))

    def _clicar_lista(self, evento: tk.Event) -> None:
        iid = self.lista.identify_row(evento.y)
        if self.rodando or not iid or self.lista.identify_region(evento.x, evento.y) != "cell":
            return
        self._definir_marca(iid, iid not in self.marcados)
        self._atualizar_contagem()

    def _marcar(self, quais: str) -> None:
        """Age só sobre os arquivos visíveis (respeita o filtro)."""
        for video in self.visiveis:
            iid = str(video)
            if quais == "todos":
                self._definir_marca(iid, True)
            elif quais == "nenhum":
                self._definir_marca(iid, False)
            elif iid not in self.feitos:  # "pendentes": soma aos já marcados
                self._definir_marca(iid, True)
        self._atualizar_contagem()

    def _selecionados(self) -> list[Path]:
        return [v for v in self.videos if str(v) in self.marcados]

    def _atualizar_contagem(self) -> None:
        n = len(self.marcados)
        texto = ""
        if self.videos:
            total = tamanho_legivel(sum(self.tamanhos[i] for i in self.marcados))
            texto = f"{n} de {len(self.videos)} selecionado(s)" + (f" · {total}" if n else "")
            if self.filtro.get().strip():
                texto += f" · {len(self.visiveis)} no filtro"
        self.contagem.configure(text=texto)
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
        refazer = [v for v in videos if str(v) in self.feitos]
        if refazer and not messagebox.askokcancel(
            "Meet Transcript",
            f"{len(refazer)} arquivo(s) marcado(s) já têm transcrição e serão refeitos "
            "(o .txt e o .srt atuais serão substituídos). Continuar?",
        ):
            return

        self.cancelar.clear()
        for botao in (self.botao_escolher, *self.botoes_selecao):
            botao.configure(state="disabled")
        self.botao_cancelar.configure(state="normal")
        self.barra["value"] = 0
        self.status.configure(text="Transcrevendo...")
        self.trabalho = threading.Thread(target=self._trabalhar, args=(videos,), daemon=True)
        self.trabalho.start()
        self._atualizar_contagem()

    def _pedir_cancelamento(self) -> None:
        self.cancelar.set()
        self.botao_cancelar.configure(state="disabled")
        self.status.configure(text="Cancelando...")

    def _abrir_pasta(self) -> None:
        pasta = self.pasta.get().strip().strip('"')
        if not pasta or not Path(pasta).is_dir():
            return
        if os.name == "nt":
            os.startfile(pasta)
        else:
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", pasta])

    def _fechar(self) -> None:
        if self.rodando:
            if not messagebox.askokcancel(
                "Meet Transcript",
                "A transcrição será cancelada. Os arquivos já concluídos ficam salvos; "
                "o que está em andamento é descartado. Sair mesmo assim?",
            ):
                return
            # Dá alguns segundos para a thread parar e apagar os arquivos .parcial.
            self._pedir_cancelamento()
            limite = time.monotonic() + 10
            while self.rodando and time.monotonic() < limite:
                self.update()
                time.sleep(0.05)
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
                cancelado=self.cancelar.is_set,
            )
            self.fila.put(("fim", n))
        except self.transcritor.Cancelamento:
            self.fila.put(("cancelado", None))
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
                    if not self.cancelar.is_set():
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
                elif tipo in ("fim", "cancelado", "erro"):
                    self._terminar(tipo, dado)
        except queue.Empty:
            pass
        self.after(100, self._processar_fila)

    def _terminar(self, tipo: str, dado) -> None:
        self.trabalho = None
        for botao in (self.botao_escolher, *self.botoes_selecao):
            botao.configure(state="normal")
        self.botao_cancelar.configure(state="disabled")
        if tipo == "fim":
            self.barra["value"] = 100
            self.status.configure(text=f"Concluído: {dado} arquivo(s) transcrito(s).")
        elif tipo == "cancelado":
            self.status.configure(text="Cancelado.")
            self._escrever("Cancelado. Os arquivos concluídos foram mantidos; o que estava em andamento foi descartado.")
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
