"""Janelinha de novo lembrete: o que lembrar e quando, com a prévia de como ele entendeu."""

import tkinter as tk
from tkinter import font as tkfont

from . import lembretes, tela
from .menu import APAGADO, BORDA, DESTAQUE, FUNDO, LARANJA, TEXTO, VERDE, VERMELHO

EXEMPLOS = "Ex.: 15:30 · amanhã 9h · daqui a 20 min · sexta 14h · 25/12 8h · todo dia 9h"


class DialogoLembrete:
    def __init__(self, mascote):
        self.m = mascote
        self.janela = None

    @property
    def aberto(self):
        return self.janela is not None

    def abrir(self):
        if self.janela is not None:
            self.janela.lift()
            self.janela.focus_force()
            return
        m, e = self.m, self.m.escala
        j = self.janela = tk.Toplevel(m.root)
        j.title("Novo lembrete")
        j.config(bg=FUNDO, padx=3 * e, pady=3 * e)
        j.attributes("-topmost", True)
        j.resizable(False, False)
        j.protocol("WM_DELETE_WINDOW", self.fechar)
        j.bind("<Escape>", lambda ev: self.fechar())
        j.bind("<Return>", lambda ev: self._salvar())

        fonte = tkfont.Font(root=m.root, family="Segoe UI", size=10)
        negrito = tkfont.Font(root=m.root, family="Segoe UI", size=10, weight="bold")
        pequena = tkfont.Font(root=m.root, family="Segoe UI", size=8)

        def rotulo(texto):
            tk.Label(j, text=texto, font=negrito, fg=TEXTO, bg=FUNDO, anchor="w").pack(fill="x", pady=(e, 0))

        def campo():
            c = tk.Entry(j, font=fonte, width=36, bg=DESTAQUE, fg=TEXTO, insertbackground=TEXTO,
                         relief="flat", highlightthickness=1, highlightbackground=BORDA, highlightcolor=LARANJA)
            c.pack(fill="x", ipady=e // 2, pady=(e // 2, 0))
            return c

        rotulo("O que lembrar?")
        self.texto = campo()
        rotulo("Quando?")
        self.quando = campo()
        self.previa = tk.Label(j, text=EXEMPLOS, font=pequena, fg=APAGADO, bg=FUNDO, anchor="w",
                               justify="left", wraplength=60 * e)
        self.previa.pack(fill="x", pady=(e // 2, 0))
        self.quando.bind("<KeyRelease>", lambda ev: self._atualizar_previa())

        botoes = tk.Frame(j, bg=FUNDO)
        botoes.pack(fill="x", pady=(2 * e, 0))
        for texto, cor, acao in (("Lembrar ⏰", LARANJA, self._salvar), ("Cancelar", BORDA, self.fechar)):
            b = tk.Label(botoes, text=texto, font=negrito, fg=TEXTO, bg=cor, padx=3 * e, pady=e,
                         cursor="hand2")
            b.pack(side="right", padx=(e, 0))
            b.bind("<Button-1>", lambda ev, a=acao: a())

        j.update_idletasks()
        # Abre perto do pet, sem sair da tela
        a = m.area
        w, h = j.winfo_reqwidth(), j.winfo_reqheight()
        x = min(max(m.corpo.x - w / 2, a.esquerda + 8), a.direita - w - 8)
        y = max(a.topo + 8, m.corpo.y - m.sprites.altura_corpo - h - 40)
        j.geometry(f"+{round(x)}+{round(y)}")
        tela.cantos_arredondados(j)
        j.focus_force()
        self.texto.focus_set()

    def fechar(self):
        if self.janela is not None:
            self.janela.destroy()
            self.janela = None

    def _atualizar_previa(self):
        escrito = self.quando.get().strip()
        if not escrito:
            self.previa.config(text=EXEMPLOS, fg=APAGADO)
            return
        quando, repetir = lembretes.interpretar(escrito)
        if quando is None:
            self.previa.config(text="Não entendi esse horário 🤔\n" + EXEMPLOS, fg=VERMELHO)
        else:
            self.previa.config(text="→ " + lembretes.formatar(quando, repetir=repetir), fg=VERDE)

    def _salvar(self):
        texto = self.texto.get().strip()
        quando, repetir = lembretes.interpretar(self.quando.get())
        if not texto:
            self.texto.focus_set()
            self.previa.config(text="Escreve o que é pra lembrar ✏️", fg=VERMELHO)
            return
        if quando is None:
            self.quando.focus_set()
            if self.quando.get().strip():
                self._atualizar_previa()
            else:
                self.previa.config(text="Falta dizer quando ⏰\n" + EXEMPLOS, fg=VERMELHO)
            return
        self.fechar()
        self.m.lembretes.adicionar(texto, quando, repetir)
