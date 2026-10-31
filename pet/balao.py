"""Balão de fala: janelinha separada que segue o Clawd e não sai da tela."""

import time
import tkinter as tk
from tkinter import font as tkfont

COR_FUNDO = "#FFFFFF"
COR_BORDA = "#1B1B1B"


class Balao:
    def __init__(self, root, cor_chave, escala):
        self.e = escala
        self.borda = max(2, escala // 2)
        self.canto = self.borda * 2          # cantinho cortado, estilo pixel
        self.ponta_h = 2 * escala            # altura do biquinho
        self.ponta_w = escala                # meia largura do biquinho
        self.pad = 2 * escala

        self.janela = tk.Toplevel(root)
        self.janela.withdraw()
        self.janela.overrideredirect(True)
        self.janela.attributes("-topmost", True)
        self.janela.attributes("-transparentcolor", cor_chave)
        self.janela.config(bg=cor_chave)
        self.canvas = tk.Canvas(self.janela, bg=cor_chave, highlightthickness=0, bd=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", lambda e: self.esconder())   # clicar no balão fecha
        self.fonte = tkfont.Font(root=root, family="Segoe UI", size=10)

        self.visivel = False
        self.ate = None          # instante em que some (None = fica até esconder)
        self.texto = ""
        self.w = self.h = 0
        self._ponta_x = None
        self._pos = None
        self._alvo = None        # última posição do Clawd recebida

    def falar(self, texto, segundos=None, fixo=False):
        """Mostra o texto. Sem `segundos`, a duração depende do tamanho do texto."""
        self.texto = texto
        self.canvas.delete("all")
        b = self.borda
        item = self.canvas.create_text(b + self.pad, b + self.pad, text=texto, anchor="nw",
                                       font=self.fonte, fill=COR_BORDA, justify="center",
                                       width=60 * self.e, tags="texto")
        x0, y0, x1, y1 = self.canvas.bbox(item)
        self.w = (x1 - x0) + 2 * self.pad + 2 * b
        self.h = (y1 - y0) + 2 * self.pad + 2 * b + self.ponta_h
        self.canvas.config(width=self.w, height=self.h)
        self._ponta_x = None
        self._pos = None
        if fixo:
            self.ate = None
        else:
            segundos = segundos or min(8.0, max(2.5, 1.5 + len(texto) * 0.06))
            self.ate = time.perf_counter() + segundos
        if self._alvo:
            self._posicionar(*self._alvo)
        if not self.visivel:
            self.janela.deiconify()
            self.visivel = True

    def esconder(self):
        if self.visivel:
            self.janela.withdraw()
            self.visivel = False
            self.texto = ""

    def atualizar(self, cx, topo_y, area):
        """Chamado a cada tick com o centro do Clawd e o topo da cabeça."""
        self._alvo = (cx, topo_y, area)
        if not self.visivel:
            return
        if self.ate is not None and time.perf_counter() >= self.ate:
            self.esconder()
            return
        self._posicionar(cx, topo_y, area)

    def _posicionar(self, cx, topo_y, area):
        wx = round(min(max(cx - self.w / 2, area.esquerda), area.direita - self.w))
        wy = round(max(area.topo, topo_y - self.h))
        # Biquinho aponta pro Clawd mesmo quando o balão encosta na borda
        margem = self.canto + self.ponta_w + self.borda
        ponta_x = round(min(max(cx - wx, margem), self.w - margem))
        if ponta_x != self._ponta_x:
            self._desenhar_forma(ponta_x)
        if (wx, wy) != self._pos:
            self.janela.geometry(f"{self.w}x{self.h}+{wx}+{wy}")
            self._pos = (wx, wy)

    def _desenhar_forma(self, px):
        self._ponta_x = px
        self.canvas.delete("forma")
        b, c, t = self.borda, self.canto, self.ponta_w
        x0, y0 = b / 2, b / 2
        x1, y1 = self.w - b / 2, self.h - self.ponta_h - b / 2
        pontos = [x0 + c, y0, x1 - c, y0, x1, y0 + c, x1, y1 - c, x1 - c, y1,
                  px + t, y1, px, y1 + self.ponta_h - b / 2, px - t, y1,
                  x0 + c, y1, x0, y1 - c, x0, y0 + c]
        self.canvas.create_polygon(pontos, fill=COR_FUNDO, outline=COR_BORDA, width=b, tags="forma")
        self.canvas.tag_lower("forma", "texto")
