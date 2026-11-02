"""Brincar de bola: aparece uma bola e o pet corre atrás e chuta.

A bola é uma janelinha transparente com a mesma física do pet quando é jogado
(gravidade, quique nas bordas, atrito no chão e pouso em cima das janelas).
Dá pra pegar a bola com o mouse e arremessar também.
"""

import math
import random
import time
import tkinter as tk

from . import config, fisica, interacao, pixelart, tela
from .janelas import velocidade_do_pulo
from .sprites import grade_para_imagem

CHUTES_POR_JOGO = (4, 7)       # quantos chutes até ele cansar (sorteado a cada jogo)
SEGUNDOS_MAX = 40              # o jogo acaba sozinho depois disso
SEGUNDOS_PARADA_NO_ALTO = 4    # bola parada onde ele não alcança: desiste
FALAS_CHUTE = ["Toma! ⚽", "Gooool! ⚽", "Chutão!", "Lá vai!", "Hehe ⚽"]


def _girar(grade):
    """A grade girada 90° (pra bola rolar)."""
    g = pixelart.Grade(grade.altura, grade.largura)
    for y, linha in enumerate(grade.px):
        for x, cor in enumerate(linha):
            if cor:
                g.ponto(grade.altura - 1 - y, x, cor)
    return g


class Bola:
    """A bola na tela: janela própria, física e o mouse."""

    def __init__(self, mascote, x, y):
        self.m = mascote
        e = mascote.escala
        grade = pixelart.BOLA
        quadros = [grade]
        for _ in range(3):
            quadros.append(_girar(quadros[-1]))
        self.imagens = [grade_para_imagem(mascote.root, q, e) for q in quadros]
        self.lado = grade.largura * e
        self.meia = self.lado / 2
        self.corpo = fisica.Corpo(x, y)
        self.giro = 0.0               # quanto já rolou (escolhe o quadro)
        self.arrastando = False
        self._apertado = None
        self._pegada = (0.0, 0.0)
        self._amostras = []
        self._pos = None

        j = self.janela = tk.Toplevel(mascote.root)
        j.withdraw()
        j.overrideredirect(True)
        j.attributes("-topmost", True)
        j.attributes("-transparentcolor", config.COR_CHAVE)
        j.config(bg=config.COR_CHAVE)
        self.canvas = tk.Canvas(j, width=self.lado, height=self.lado, bg=config.COR_CHAVE,
                                highlightthickness=0, bd=0, cursor="hand2")
        self.canvas.pack()
        self.item = self.canvas.create_image(0, 0, anchor="nw", image=self.imagens[0])
        self.canvas.bind("<ButtonPress-1>", self._apertou)
        self.canvas.bind("<B1-Motion>", self._moveu)
        self.canvas.bind("<ButtonRelease-1>", self._soltou)
        self._posicionar()
        j.deiconify()
        j.update_idletasks()
        tela.estilo_ferramenta(j)

    # ------------------------------------------------------------------ física

    @property
    def parada(self):
        return self.corpo.no_chao and self.corpo.vx == 0 and not self.arrastando

    def chao(self):
        """Chão embaixo da bola: janela ou barra de tarefas (igual ao do pet)."""
        return self.m.janelas.plataformas.chao_abaixo(self.corpo.x, self.corpo.y, self.m.area, self.lado)

    def chutar(self, vx, vy):
        self.corpo.vx, self.corpo.vy = vx, vy
        self.corpo.no_chao = False

    def tick(self, dt):
        if self.arrastando:
            return
        c = self.corpo
        a = self.m.area
        chao, _ = self.chao()
        if c.no_chao and chao > c.y + 1:
            c.no_chao = False                  # a janela embaixo sumiu (ou rolou pra fora dela)
        lim = fisica.Limites(a.esquerda, a.direita, a.topo, chao, self.meia, self.lado)
        x_antes = c.x
        fisica.passo(c, lim, self.m.params, dt)
        self.giro += (c.x - x_antes) / self.meia            # rola conforme anda
        self._posicionar()

    def _posicionar(self):
        quadro = int(self.giro) % 4
        self.canvas.itemconfig(self.item, image=self.imagens[quadro])
        pos = (round(self.corpo.x - self.meia), round(self.corpo.y - self.lado))
        if pos != self._pos:
            self.janela.geometry(f"+{pos[0]}+{pos[1]}")
            self._pos = pos

    def fechar(self):
        try:
            self.janela.destroy()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ mouse (pegar e arremessar)

    def _apertou(self, e):
        self._apertado = (e.x_root, e.y_root)
        self._pegada = (e.x_root - self.corpo.x, e.y_root - self.corpo.y)
        self._amostras = [(time.perf_counter(), e.x_root, e.y_root)]

    def _moveu(self, e):
        if self._apertado is None:
            return
        if not self.arrastando:
            if not interacao.eh_arrasto(self._apertado, (e.x_root, e.y_root), config.LIMIAR_CLIQUE):
                return
            self.arrastando = True
        agora = time.perf_counter()
        self.corpo.x = e.x_root - self._pegada[0]
        self.corpo.y = e.y_root - self._pegada[1]
        self._amostras.append((agora, e.x_root, e.y_root))
        self._amostras = [a for a in self._amostras if agora - a[0] <= 0.25]
        self._posicionar()

    def _soltou(self, e):
        if self._apertado is None:
            return
        self._apertado = None
        if not self.arrastando:
            # Clique na bola: um toquinho pra cima
            self.chutar(random.uniform(-200, 200) * self.m.k, -700 * self.m.k)
            return
        self.arrastando = False
        vx, vy = interacao.estimar_velocidade(self._amostras, time.perf_counter())
        if math.hypot(vx, vy) < config.LIMIAR_ARREMESSO * self.m.k:
            vx = vy = 0.0
        self.chutar(*fisica.limitar_velocidade(vx, vy, self.m.params.vel_max))


class Brincadeira:
    """O jogo: o pet corre até a bola, chuta, e depois de uns chutes cansa e a bola some."""

    def __init__(self, mascote):
        self.m = mascote
        self.bola = None
        self.chutes = 0
        self.meta = 0
        self.fim = 0.0
        self._parada_no_alto = None
        self._chute_em = None          # instante em que o pé encosta na bola

    @property
    def ativa(self):
        return self.bola is not None

    def comecar(self):
        m = self.m
        self.parar(falar=False)
        self.chutes = 0
        self.meta = random.randint(*CHUTES_POR_JOGO)
        self.fim = time.time() + SEGUNDOS_MAX
        self._parada_no_alto = None
        # A bola cai do alto, na frente dele (do lado que tem mais espaço)
        a = m.area
        lado = m.direcao if a.esquerda + 200 * m.k < m.corpo.x + m.direcao * 160 * m.k < a.direita - 200 * m.k \
            else -m.direcao
        x = m.corpo.x + lado * 160 * m.k
        self.bola = Bola(m, x, m.corpo.y - 160 * m.k)
        self.bola.corpo.vy = 0.0
        m.direcao = lado
        m.mudar("parado")

    def parar(self, falar=True):
        if self.bola is None:
            return
        self.bola.fechar()
        self.bola = None
        self._chute_em = None
        m = self.m
        if falar and m.acao in ("parado", "correndo", "chutando"):
            m.mudar("comemorando", 2)
            m.falar("Que jogo bom! ⚽", 2)
        elif m.acao in ("correndo", "chutando"):
            m.mudar("parado", 1.5)

    # ------------------------------------------------------------------ todo tick

    def tick(self, dt):
        if self.bola is None:
            return
        m = self.m
        bola = self.bola
        bola.tick(dt)
        agora = time.time()
        # Coisas mais importantes que a bola: lembrete, Claude chamando, escondido da tela cheia
        if m.lembretes.ativo is not None or m.cc.esperando or m.tela_cheia.escondido:
            self.parar(falar=False)
            return
        if agora > self.fim or (self.chutes >= self.meta and bola.parada):
            self.parar()
            return
        if self._chute_em is not None:
            if agora >= self._chute_em:
                self._chute_em = None
                self._chutar()
            return
        if m.acao not in ("parado", "correndo", "andando", "digitando"):
            return                                     # sendo arrastado, caindo, comemorando...
        self._correr_atras()

    def _correr_atras(self):
        m, bola = self.m, self.bola
        dx = bola.corpo.x - m.corpo.x
        perto = abs(dx) <= m.sprites.meia_largura + bola.meia * 0.6
        mesmo_chao = abs(bola.corpo.y - m.corpo.y) <= 3 * m.k
        if bola.corpo.no_chao and not bola.arrastando:
            if bola.corpo.y > m.corpo.y + 3 * m.k:
                # Bola lá embaixo e ele numa janela: pula pra baixo
                self._parada_no_alto = None
                m.direcao = 1 if dx >= 0 else -1
                m.cair()
                return
            if bola.corpo.y < m.corpo.y - 3 * m.k:
                self._pular_ate_a_bola()
                return
        self._parada_no_alto = None
        if perto and mesmo_chao and abs(bola.corpo.vx) < 300 * m.k:
            m.direcao = 1 if dx >= 0 else -1
            m.mudar("chutando", 0.45)
            self._chute_em = time.time() + 0.15        # o pé chega na bola um pouquinho depois
            return
        if abs(dx) > 4 * m.k:
            m.direcao = 1 if dx > 0 else -1
            if m.acao != "correndo":
                m.mudar("correndo")
        elif m.acao != "parado":
            m.mudar("parado")

    def _pular_ate_a_bola(self):
        """Bola parada numa janela mais alta: pula pra perto dela, ou desiste se não alcança."""
        m, bola = self.m, self.bola
        agora = time.time()
        alcance = config.ALCANCE_PULO * m.k
        if m.corpo.y - bola.corpo.y > alcance:
            if self._parada_no_alto is None:
                self._parada_no_alto = agora
            elif agora - self._parada_no_alto > SEGUNDOS_PARADA_NO_ALTO:
                self.parar(falar=False)
                m.falar("A bola ficou lá em cima! 😅", 2.5)
            if m.acao != "parado":
                m.mudar("parado")
            return
        lado = 1 if bola.corpo.x >= m.corpo.x else -1
        alvo_x = bola.corpo.x - lado * (m.sprites.meia_largura + bola.meia)
        vx, vy = velocidade_do_pulo(m.corpo.x, m.corpo.y, alvo_x, bola.corpo.y, m.params.gravidade, 40 * m.k)
        m.pular(vx, vy)

    def _chutar(self):
        m, bola = self.m, self.bola
        if bola is None or abs(bola.corpo.x - m.corpo.x) > m.sprites.meia_largura + bola.lado:
            return                                       # a bola fugiu antes do pé chegar
        forca = random.uniform(0.6, 1.3)
        bola.chutar(m.direcao * 900 * forca * m.k, -random.uniform(500, 1100) * m.k)
        self.chutes += 1
        m.tama.ganhar_xp(1)
        m._ajustar("felicidade", 2)
        if random.random() < 0.4 and not m.balao.visivel:
            m.falar(random.choice(FALAS_CHUTE), 1.2)
