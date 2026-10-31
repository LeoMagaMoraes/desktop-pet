"""Gotas de chuva caindo na tela, numa janela transparente que os cliques atravessam."""

import random
import tkinter as tk

from . import tela

COR_GOTA = "#9CC3E8"

# categoria do clima -> (quantas gotas, velocidade em px/s na escala 4, comprimento em pixels da grade)
INTENSIDADE = {"garoa": (60, 350, 2), "chuva": (140, 650, 3), "tempestade": (200, 950, 4)}


class ChuvaNaTela:
    def __init__(self, root, cor_chave, escala):
        self.root = root
        self.cor_chave = cor_chave
        self.e = escala
        self.k = escala / 4
        self.janela = None
        self.canvas = None
        self.gotas = []          # [item, x, y, velocidade]
        self.categoria = None
        self.area = None

    @property
    def ativa(self):
        return self.janela is not None

    def ajustar(self, categoria, area):
        """Liga, desliga ou muda a intensidade. categoria None (ou sem chuva) desliga."""
        if categoria not in INTENSIDADE:
            self.desligar()
            return
        if self.janela is None or area != self.area:
            self.desligar()
            self._criar(area)
        if categoria != self.categoria:
            self.categoria = categoria
            self._semear()

    def desligar(self):
        if self.janela is not None:
            self.janela.destroy()
        self.janela = self.canvas = None
        self.gotas = []
        self.categoria = None

    def _criar(self, area):
        self.area = area
        largura, altura = area.direita - area.esquerda, area.base - area.topo
        j = self.janela = tk.Toplevel(self.root)
        j.withdraw()
        j.overrideredirect(True)
        j.attributes("-topmost", True)
        j.attributes("-transparentcolor", self.cor_chave)
        j.attributes("-alpha", 0.55)           # gota meio transparente, mais discreta
        j.config(bg=self.cor_chave)
        j.geometry(f"{largura}x{altura}+{area.esquerda}+{area.topo}")
        self.canvas = tk.Canvas(j, width=largura, height=altura, bg=self.cor_chave,
                                highlightthickness=0, bd=0)
        self.canvas.pack()
        j.deiconify()
        j.update_idletasks()
        tela.atravessar_cliques(j)

    def _semear(self):
        """Cria as gotas espalhadas pela tela toda (sem esperar elas caírem do topo)."""
        self.canvas.delete("all")
        quantas, _, _ = INTENSIDADE[self.categoria]
        largura, altura = self.area.direita - self.area.esquerda, self.area.base - self.area.topo
        self.gotas = []
        for _ in range(quantas):
            x, y = random.uniform(0, largura), random.uniform(0, altura)
            item = self.canvas.create_line(0, 0, 0, 0, fill=COR_GOTA, width=max(1, self.e // 2))
            self.gotas.append([item, x, y, random.uniform(0.75, 1.25)])

    def atualizar(self, dt):
        if self.janela is None:
            return
        _, velocidade, comprimento = INTENSIDADE[self.categoria]
        largura, altura = self.area.direita - self.area.esquerda, self.area.base - self.area.topo
        tamanho = comprimento * self.e
        for gota in self.gotas:
            item, x, y, fator = gota
            vy = velocidade * self.k * fator
            y += vy * dt
            x -= vy * 0.15 * dt                 # ventinho: cai um pouco inclinada
            if y > altura:                      # bateu no chão: volta lá pra cima
                y = random.uniform(-altura * 0.2, 0)
                x = random.uniform(0, largura * 1.1)
            if x < 0:
                x += largura
            gota[1], gota[2] = x, y
            self.canvas.coords(item, x, y, x + tamanho * 0.15, y - tamanho)
