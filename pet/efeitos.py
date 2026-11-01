"""Partículas em volta do pet: coração, Zzz, migalhas, bolhas, gotas, notinhas, confete, estrelinhas e mosquinhas."""

import math
import random


class _Particula:
    __slots__ = ("item", "x", "y", "vx", "vy", "vida", "idade", "gravidade", "balanco", "fase")


class Efeitos:
    def __init__(self, canvas, imagens, item_sprite, k):
        self.canvas = canvas
        self.imagens = imagens
        self.item_sprite = item_sprite
        self.k = k                # fator de escala da tela
        self.particulas = []
        self.estrelas = []
        self.angulo = 0.0
        self.moscas = []
        self.ventilador = None      # item do ventiladorzinho (calor), ou None
        self.tempo = 0.0

    def _soltar(self, tipo, x, y, vx, vy, vida, gravidade=0.0, balanco=0.0):
        p = _Particula()
        p.item = self.canvas.create_image(x, y, image=self.imagens[tipo])
        p.x, p.y, p.vx, p.vy = x, y, vx, vy
        p.vida, p.idade = vida, 0.0
        p.gravidade, p.balanco = gravidade, balanco
        p.fase = random.uniform(0, math.tau)
        self.particulas.append(p)

    def coracao(self, x, y):
        k = self.k
        self._soltar("coracao", x + random.uniform(-6, 6) * k, y, 0, -55 * k, 1.1, balanco=6 * k)

    def zzz(self, x, y, direcao):
        k = self.k
        self._soltar("zzz", x, y, 16 * k * direcao, -26 * k, 1.8, balanco=3 * k)

    def migalhas(self, x, y):
        k = self.k
        for _ in range(3):
            self._soltar("migalha", x, y, random.uniform(-50, 50) * k,
                         random.uniform(-120, -50) * k, 0.8, gravidade=600 * k)

    def bolha(self, x, y):
        k = self.k
        self._soltar("bolha", x, y, random.uniform(-15, 15) * k, -35 * k, 0.9, balanco=4 * k)

    def gotas(self, x, y, direcao, tipo="gota"):
        """Espirro: gotinhas (ou faíscas, no dragão) saindo pra frente."""
        k = self.k
        for _ in range(4):
            self._soltar(tipo, x, y, direcao * random.uniform(60, 140) * k,
                         random.uniform(-80, -10) * k, 0.6, gravidade=500 * k)

    def fumaca(self, x, y):
        """Nuvenzinha de fumaça (troca de pet)."""
        k = self.k
        for _ in range(8):
            self._soltar("fumaca", x + random.uniform(-30, 30) * k, y + random.uniform(-20, 20) * k,
                         random.uniform(-40, 40) * k, random.uniform(-60, -20) * k, 0.9, balanco=4 * k)

    def nota(self, x, y, direcao):
        """Notinha musical subindo e balançando (música tocando)."""
        k = self.k
        tipo = random.choice(("nota", "nota_b"))
        self._soltar(tipo, x, y, direcao * random.uniform(10, 25) * k, -30 * k, 1.6, balanco=5 * k)

    def confete(self, x, y):
        """Chuvinha de confete colorido (aniversário, Ano Novo, Carnaval)."""
        k = self.k
        for _ in range(14):
            self._soltar(random.choice(("confete_r", "confete_y", "confete_a", "confete_e")),
                         x + random.uniform(-10, 10) * k, y, random.uniform(-90, 90) * k,
                         random.uniform(-260, -140) * k, 1.4, gravidade=380 * k, balanco=3 * k)

    def quantidade_moscas(self, n):
        """Deixa exatamente n mosquinhas voando em volta dele."""
        while len(self.moscas) < n:
            self.moscas.append(self.canvas.create_image(-50, -50, image=self.imagens["mosca"]))
        while len(self.moscas) > n:
            self.canvas.delete(self.moscas.pop())

    def ventilador_ligado(self, ligar):
        if ligar and self.ventilador is None:
            self.ventilador = self.canvas.create_image(-50, -50, image=self.imagens["ventilador_a"])
        elif not ligar and self.ventilador is not None:
            self.canvas.delete(self.ventilador)
            self.ventilador = None

    def estrelas_girando(self, ligar):
        if ligar and not self.estrelas:
            self.estrelas = [self.canvas.create_image(-50, -50, image=self.imagens["estrela"])
                             for _ in range(3)]
        elif not ligar:
            for item in self.estrelas:
                self.canvas.delete(item)
            self.estrelas = []

    def atualizar(self, dt, cabeca_x, cabeca_y, centro_y):
        """Move as partículas; estrelas giram na cabeça e moscas voam em volta do corpo."""
        self.tempo += dt
        vivas = []
        for p in self.particulas:
            p.idade += dt
            if p.idade >= p.vida:
                self.canvas.delete(p.item)
                continue
            p.vy += p.gravidade * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            onda = math.sin(p.idade * 7 + p.fase) * p.balanco
            self.canvas.coords(p.item, p.x + onda, p.y)
            vivas.append(p)
        self.particulas = vivas

        if self.estrelas:
            self.angulo += dt * 4.5
            rx, ry = 9 * 4 * self.k, 2.5 * 4 * self.k
            for i, item in enumerate(self.estrelas):
                a = self.angulo + i * math.tau / 3
                self.canvas.coords(item, cabeca_x + math.cos(a) * rx, cabeca_y + math.sin(a) * ry)
                # Metade da volta passa na frente do Clawd, metade atrás
                if math.sin(a) > 0:
                    self.canvas.tag_raise(item, self.item_sprite)
                else:
                    self.canvas.tag_lower(item, self.item_sprite)

        # Ventiladorzinho flutuando do lado da cabeça, com as pás girando
        if self.ventilador is not None:
            quadro = "ventilador_a" if int(self.tempo * 10) % 2 else "ventilador_b"
            self.canvas.itemconfig(self.ventilador, image=self.imagens[quadro])
            self.canvas.coords(self.ventilador, cabeca_x + 11 * 4 * self.k,
                               cabeca_y + math.sin(self.tempo * 3) * 2 * self.k)

        # Mosquinhas: cada uma num zigue-zague diferente em volta do corpo
        rx, ry = 11 * 4 * self.k, 6 * 4 * self.k
        for i, item in enumerate(self.moscas):
            t = self.tempo
            x = cabeca_x + math.sin(t * (2.3 + i * 0.7) + i * 2.1) * rx + math.sin(t * 9 + i) * 2 * self.k
            y = centro_y + math.cos(t * (1.7 + i * 0.5) + i) * ry + math.cos(t * 11 + i) * 2 * self.k
            self.canvas.coords(item, x, y)
