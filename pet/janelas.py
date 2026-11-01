"""Andar em cima das janelas: a borda de cima de cada janela vira um chão.

Plataformas é só lógica (dá pra testar com janelas de mentira). Explorador liga
isso ao pet: pousar nas janelas, seguir a janela quando você arrasta, cair
quando ela some e pular pra cima de uma de vez em quando.
"""

import math
import random
import time

from . import config, tela


class Plataformas:
    """As janelas abertas, da mais da frente pra mais do fundo."""

    def __init__(self, janelas=()):
        self.atualizar(janelas)

    def atualizar(self, janelas):
        self.janelas = list(janelas)
        self._indice = {j.hwnd: i for i, j in enumerate(self.janelas)}

    def janela(self, hwnd):
        i = self._indice.get(hwnd)
        return None if i is None else self.janelas[i]

    def _coberto(self, indice, x, y):
        """Alguma janela mais da frente tapa o ponto (x, y)?"""
        return any(j.esquerda <= x < j.direita and j.topo <= y < j.base for j in self.janelas[:indice])

    def _cabe(self, j, area, altura):
        """A borda está dentro da área útil e sobra espaço pro pet em cima dela."""
        return j.topo - altura >= area.topo and j.topo < area.base

    def superficie(self, hwnd, x, area, altura):
        """Altura do chão da janela `hwnd` no ponto x, ou None se ali não dá pra pisar."""
        i = self._indice.get(hwnd)
        if i is None:
            return None
        j = self.janelas[i]
        if not (j.esquerda <= x < j.direita) or not area.esquerda <= x < area.direita:
            return None
        if not self._cabe(j, area, altura) or self._coberto(i, x, j.topo - 1):
            return None
        return j.topo

    def chao_abaixo(self, x, y, area, altura, ignorar=None):
        """(altura do chão, hwnd) mais alto que está abaixo dos pés em (x, y).
        Sem janela embaixo, o chão é a barra de tarefas (hwnd None).
        `ignorar` é a janela de onde ele acabou de pular (pra não pousar nela de novo)."""
        melhor = (area.base, None)
        for i, j in enumerate(self.janelas):
            if j.hwnd == ignorar or j.topo < y - 1 or j.topo >= melhor[0]:
                continue
            if j.esquerda <= x < j.direita and self.superficie(j.hwnd, x, area, altura) is not None:
                melhor = (j.topo, j.hwnd)
        return melhor

    def destinos(self, x, y, area, altura, meia, alcance, atual=None):
        """Lugares em cima de janelas pra onde dá pra pular: [(x, topo, hwnd)]."""
        saida = []
        for j in self.janelas:
            if j.hwnd == atual or abs(y - j.topo) > alcance or abs(y - j.topo) < 4:
                continue
            esq = max(j.esquerda, area.esquerda) + meia + 4
            dir_ = min(j.direita, area.direita) - meia - 4
            if dir_ <= esq:
                continue
            alvo = random.uniform(esq, dir_)
            if self.superficie(j.hwnd, alvo, area, altura) is not None:
                saida.append((alvo, j.topo, j.hwnd))
        return saida


def velocidade_do_pulo(x, y, alvo_x, alvo_y, gravidade, folga):
    """(vx, vy) pra sair de (x, y) e cair em (alvo_x, alvo_y), passando `folga` acima do mais alto."""
    topo = min(y, alvo_y) - folga
    vy = -math.sqrt(2 * gravidade * (y - topo))
    subindo = -vy / gravidade
    descendo = math.sqrt(2 * (alvo_y - topo) / gravidade)
    return (alvo_x - x) / (subindo + descendo), vy


class Explorador:
    """Liga as plataformas ao pet."""

    def __init__(self, mascote):
        self.m = mascote
        self.plataformas = Plataformas()
        self.hwnd = None              # janela em que ele está (None = barra de tarefas)
        self._saindo_de = None        # janela de onde pulou/caiu (não pousa nela de novo na hora)
        self._ultima = None           # retângulo dela na última olhada (pra seguir quando mexe)
        self._prox_leitura = 0.0
        self.atualizar(forcar=True)

    @property
    def ligado(self):
        return self.m.estado.dados.get("andar_nas_janelas", True)

    def atualizar(self, forcar=False):
        agora = time.perf_counter()
        if not forcar and agora < self._prox_leitura:
            return
        # Em cima de uma janela olha mais vezes, pra pegar carona suave quando você arrasta ela
        intervalo = config.JANELAS_MS if self.hwnd is None else config.JANELAS_EM_CIMA_MS
        self._prox_leitura = agora + intervalo / 1000
        self.plataformas.atualizar(tela.janelas_visiveis() if self.ligado else [])

    def _medidas(self):
        return self.m.area, self.m.sprites.altura_corpo

    # ------------------------------------------------------------------ física

    def chao(self, x, y):
        """Chão pra física: a janela mais alta embaixo dos pés, ou a barra de tarefas."""
        area, altura = self._medidas()
        return self.plataformas.chao_abaixo(x, y, area, altura, ignorar=self._saindo_de)

    def pousou(self, x, y):
        """Anota em que janela ele parou (se parou numa)."""
        topo, hwnd = self.chao(x, y)
        self.hwnd = hwnd if abs(topo - y) <= 2 else None
        self._saindo_de = None
        self._ultima = self.plataformas.janela(self.hwnd) if self.hwnd else None

    def soltar(self, saindo=False):
        """Saiu do chão. saindo=True quando ele pulou ou caiu da janela por conta própria
        (aí ela fica de fora até ele pousar); arrastado pela mão, pode voltar pra mesma."""
        self._saindo_de = self.hwnd if saindo else None
        self.hwnd = None
        self._ultima = None

    # ------------------------------------------------------------------ andando

    def pode_andar(self, novo_x):
        """'ok', 'virar' (chegou na beirada) ou 'cair'. Na barra de tarefas é sempre 'ok'."""
        if self.hwnd is None:
            return "ok"
        area, altura = self._medidas()
        if self.plataformas.janela(self.hwnd) is None:
            return "cair"
        if self.plataformas.superficie(self.hwnd, novo_x, area, altura) is not None:
            return "ok"
        return "cair" if random.random() < config.CHANCE_PULAR_DA_BEIRADA else "virar"

    # ------------------------------------------------------------------ todo tick

    def alternar(self):
        """Liga/desliga pelo menu; desligando em cima de uma janela, ele cai."""
        d = self.m.estado.dados
        d["andar_nas_janelas"] = not self.ligado
        self.atualizar(forcar=True)
        if not self.ligado and self.hwnd is not None:
            self.m.cair()

    def tick(self):
        """Segue a janela quando ela mexe e cai quando ela some ou é tapada."""
        self.atualizar()
        m = self.m
        if self.hwnd is None or m.acao in ("pendurado", "caindo"):
            return
        j = self.plataformas.janela(self.hwnd)
        area, altura = self._medidas()
        if j is not None and self._ultima is not None and (j.esquerda, j.topo) != (self._ultima.esquerda,
                                                                                    self._ultima.topo):
            m.corpo.x += j.esquerda - self._ultima.esquerda      # pega carona na janela
            m.corpo.y = j.topo
        self._ultima = j
        if j is None or self.plataformas.superficie(self.hwnd, m.corpo.x, area, altura) is None:
            m.cair()

    def tentar_pular(self):
        """De vez em quando pula pra cima de uma janela. Devolve True se pulou."""
        if not self.ligado or random.random() >= config.CHANCE_SUBIR_NA_JANELA:
            return False
        m = self.m
        area, altura = self._medidas()
        alcance = config.ALCANCE_PULO * m.k
        destinos = self.plataformas.destinos(m.corpo.x, m.corpo.y, area, altura, m.sprites.meia_largura,
                                             alcance, atual=self.hwnd)
        if not destinos:
            return False
        alvo_x, alvo_y, _ = random.choice(destinos)
        vx, vy = velocidade_do_pulo(m.corpo.x, m.corpo.y, alvo_x, alvo_y, m.params.gravidade, 40 * m.k)
        m.pular(vx, vy)
        return True
