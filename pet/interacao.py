"""Lógica do mouse sem Tk: clique x arrasto, velocidade de arremesso e sacudida."""

import math
from collections import deque


def distancia(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def eh_arrasto(inicio, atual, limiar=5):
    """Andou `limiar` pixels ou mais desde que apertou: é arrasto."""
    return distancia(inicio, atual) >= limiar


def estimar_velocidade(amostras, agora, janela=0.1, parado_ha=0.08):
    """Velocidade (px/s) do último trecho do movimento.

    amostras: lista de (tempo, x, y). Se o mouse ficou parado antes de soltar
    (última amostra mais velha que `parado_ha`), a velocidade é zero.
    """
    if len(amostras) < 2 or agora - amostras[-1][0] > parado_ha:
        return 0.0, 0.0
    t1, x1, y1 = amostras[-1]
    recentes = [a for a in amostras if t1 - a[0] <= janela]
    t0, x0, y0 = recentes[0]
    dt = t1 - t0
    if dt < 0.01:
        return 0.0, 0.0
    return (x1 - x0) / dt, (y1 - y0) / dt


class _Eixo:
    """Conta as trocas de direção num eixo, ignorando tremidinhas menores que `amplitude`."""

    def __init__(self, amplitude):
        self.amplitude = amplitude
        self.direcao = 0
        self.extremo = None

    def adicionar(self, p):
        if self.extremo is None:
            self.extremo = p
            return False
        if self.direcao == 0:
            if abs(p - self.extremo) >= self.amplitude:
                self.direcao = 1 if p > self.extremo else -1
                self.extremo = p
            return False
        if (p - self.extremo) * self.direcao > 0:
            self.extremo = p          # continua indo pro mesmo lado
            return False
        if abs(p - self.extremo) >= self.amplitude:
            self.direcao = -self.direcao
            self.extremo = p
            return True               # voltou o suficiente: trocou de direção
        return False


class DetectorSacudida:
    """Diz se o Clawd foi chacoalhado: muitas trocas de direção em pouco tempo."""

    def __init__(self, reversoes=6, janela=1.6, amplitude=30):
        self.reversoes = reversoes
        self.janela = janela
        self.amplitude = amplitude
        self.reiniciar()

    def reiniciar(self):
        self._x = _Eixo(self.amplitude)
        self._y = _Eixo(self.amplitude)
        self._trocas = deque()

    def adicionar(self, t, x, y):
        for eixo, p in ((self._x, x), (self._y, y)):
            if eixo.adicionar(p):
                self._trocas.append(t)
        while self._trocas and t - self._trocas[0] > self.janela:
            self._trocas.popleft()
        return len(self._trocas) >= self.reversoes
