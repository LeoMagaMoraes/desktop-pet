"""Gravidade, arremesso e quiques. Funções puras, sem Tk, pra dar pra testar.

Coordenadas em pixels de tela: x é o centro do Clawd, y é a linha dos pés.
"""

import math
from dataclasses import dataclass


@dataclass
class Corpo:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    no_chao: bool = False


@dataclass(frozen=True)
class Limites:
    esquerda: float
    direita: float
    topo: float
    chao: float
    meia_largura: float
    altura: float


@dataclass(frozen=True)
class Parametros:
    gravidade: float = 2600
    quique_parede: float = 0.55
    quique_chao: float = 0.4
    atrito_chao: float = 2200
    vel_min_quique: float = 260
    vel_parar: float = 20
    vel_max: float = 4500


def limitar_velocidade(vx, vy, vmax):
    """Reduz o vetor pra no máximo vmax, mantendo a direção."""
    v = math.hypot(vx, vy)
    if v <= vmax or v == 0:
        return vx, vy
    return vx * vmax / v, vy * vmax / v


def passo(c, lim, p, dt):
    """Avança a física em dt segundos. Devolve eventos [(nome, velocidade)]:
    'parede', 'teto', 'quique' e 'pousou' (quando parou de vez no chão)."""
    eventos = []
    if not c.no_chao:
        c.vy += p.gravidade * dt
    c.x += c.vx * dt
    c.y += c.vy * dt

    # Paredes laterais
    if c.x - lim.meia_largura < lim.esquerda:
        c.x = lim.esquerda + lim.meia_largura
        if c.vx < 0:
            eventos.append(("parede", -c.vx))
            c.vx = -c.vx * p.quique_parede
    elif c.x + lim.meia_largura > lim.direita:
        c.x = lim.direita - lim.meia_largura
        if c.vx > 0:
            eventos.append(("parede", c.vx))
            c.vx = -c.vx * p.quique_parede

    # Teto
    if c.y - lim.altura < lim.topo:
        c.y = lim.topo + lim.altura
        if c.vy < 0:
            eventos.append(("teto", -c.vy))
            c.vy = -c.vy * p.quique_parede

    # Chão: quica se veio rápido, senão assenta
    if c.y >= lim.chao:
        c.y = lim.chao
        if not c.no_chao:
            if c.vy > p.vel_min_quique:
                eventos.append(("quique", c.vy))
                c.vy = -c.vy * p.quique_chao
                c.vx *= 0.8
            else:
                c.vy = 0.0
                c.no_chao = True

    # Escorregando no chão até parar
    if c.no_chao:
        c.vy = 0.0
        reducao = p.atrito_chao * dt
        c.vx = 0.0 if abs(c.vx) <= reducao else c.vx - math.copysign(reducao, c.vx)
        if abs(c.vx) < p.vel_parar:
            c.vx = 0.0
            eventos.append(("pousou", 0.0))
    return eventos
