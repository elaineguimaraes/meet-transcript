"""Interface gráfica: escolha a pasta com as gravações e clique em Transcrever."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Meet Transcript")
        self.minsize(640, 440)

        self.fila: queue.Queue = queue.Queue()  # mensagens da thread de trabalho para a tela
        self.transcritor = None                 # módulo transcrever, importado em segundo plano
        self.rodando = False
        self.pasta = tk.StringVar()
        self.refazer = tk.BooleanVar(value=False)

        self._montar_tela()
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        # Importar o faster-whisper leva alguns segundos; a janela abre antes.
        threading.Thread(target=self._importar_transcritor, daemon=True).start()
        self.after(100, self._processar_fila)

    # ------------------------------------------------------------------ tela

    def _montar_tela(self) -> None:
        raiz = ttk.Frame(self, padding=12)
        raiz.pack(fill="both", expand=True)
        raiz.columnconfigure(0, weight=1)
        raiz.rowconfigure(5, weight=1)

        ttk.Label(raiz, text="Pasta com as gravações:").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Entry(raiz, textvariable=self.pasta).grid(row=1, column=0, sticky="ew", pady=(2, 6))
        self.botao_escolher = ttk.Button(raiz, text="Escolher...", command=self._escolher_pasta)
        self.botao_escolher.grid(row=1, column=1, padx=(6, 0), pady=(2, 6))

        ttk.Checkbutton(
            raiz, text="Refazer arquivos que já têm transcrição", variable=self.refazer
        ).grid(row=2, column=0, columnspan=2, sticky="w")

        acoes = ttk.Frame(raiz)
        acoes.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        self.botao_transcrever = ttk.Button(
            acoes, text="Transcrever", command=self._iniciar, state="disabled"
        )
        self.botao_transcrever.pack(side="left")
        self.botao_abrir = ttk.Button(acoes, text="Abrir pasta", command=self._abrir_pasta)
        self.botao_abrir.pack(side="left", padx=(6, 0))
        self.status = ttk.Label(acoes, text="Preparando...")
        self.status.pack(side="left", padx=(12, 0))

        self.barra = ttk.Progressbar(raiz, maximum=100)
        self.barra.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        self.log = ScrolledText(raiz, height=14, state="disabled", wrap="word")
        self.log.grid(row=5, column=0, columnspan=2, sticky="nsew")

    def _escrever(self, texto: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", texto + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    # ----------------------------------------------------------------- ações

    def _escolher_pasta(self) -> None:
        escolhida = filedialog.askdirectory(title="Escolha a pasta com as gravações")
        if not escolhida:
            return
        self.pasta.set(str(Path(escolhida)))
        if self.transcritor:
            videos = self.transcritor.listar_videos(Path(escolhida))
            self._escrever(f"{len(videos)} arquivo(s) de vídeo/áudio em {Path(escolhida)}:")
            for video in videos:
                feito = " (já transcrito)" if video.with_suffix(".txt").exists() else ""
                self._escrever(f"  - {video.name}{feito}")

    def _iniciar(self) -> None:
        pasta = Path(self.pasta.get().strip().strip('"'))
        if not self.pasta.get().strip() or not pasta.is_dir():
            messagebox.showwarning("Meet Transcript", "Escolha uma pasta válida primeiro.")
            return

        self.rodando = True
        for botao in (self.botao_transcrever, self.botao_escolher):
            botao.configure(state="disabled")
        self.barra["value"] = 0
        self.status.configure(text="Transcrevendo...")
        threading.Thread(target=self._trabalhar, args=(pasta, self.refazer.get()), daemon=True).start()

    def _abrir_pasta(self) -> None:
        pasta = self.pasta.get().strip()
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

    def _trabalhar(self, pasta: Path, refazer: bool) -> None:
        try:
            n = self.transcritor.transcrever_pasta(
                pasta,
                log=lambda texto: self.fila.put(("log", texto)),
                progresso=lambda i, total, fracao: self.fila.put(("progresso", (i, total, fracao))),
                refazer=refazer,
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
                    self.botao_transcrever.configure(state="normal")
                    self.status.configure(text="Pronto.")
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
        for botao in (self.botao_transcrever, self.botao_escolher):
            botao.configure(state="normal")
        if tipo == "fim":
            self.barra["value"] = 100
            self.status.configure(text=f"Concluído: {dado} arquivo(s) transcrito(s).")
        else:
            self.status.configure(text="Erro.")
            self._escrever(f"ERRO: {dado}")
            messagebox.showerror("Meet Transcript", dado)


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
