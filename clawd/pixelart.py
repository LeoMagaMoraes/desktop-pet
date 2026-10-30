"""Clawd provisório em pixel art, desenhado direto no código.

Cada quadro é uma Grade de cores (None = transparente), virada pra direita.
Quando existirem PNGs em sprites/<animacao>/, eles substituem estes desenhos.
"""

LARGURA = 22   # colunas da grade
ALTURA = 14    # linhas da grade; os pés ficam na última linha

# Paleta
LARANJA = "#D97757"
SOMBRA = "#B5583B"
PRETO = "#1B1B1B"
BRANCO = "#FFFFFF"
ROSA = "#F4A3A3"

# Geometria do corpo, em pixels da grade (o lado direito é o espelho do esquerdo)
CORPO_X0, CORPO_X1 = 4, 17
CORPO_TOPO = 3
CORPO_ALTURA = 8
PERNAS_X = (5, 7, 14, 16)
OLHO_X = 7          # olho esquerdo; o direito fica em LARGURA - 1 - OLHO_X


class Grade:
    """Matriz de cores de um quadro."""

    def __init__(self, largura, altura):
        self.largura = largura
        self.altura = altura
        self.px = [[None] * largura for _ in range(altura)]

    def ponto(self, x, y, cor):
        # Ignora o que cai fora da grade, assim dá pra desenhar "cortado"
        if 0 <= x < self.largura and 0 <= y < self.altura:
            self.px[y][x] = cor

    def retangulo(self, x0, y0, x1, y1, cor):
        # Limites inclusivos
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.ponto(x, y, cor)

    def pixels_pintados(self):
        return sum(1 for linha in self.px for cor in linha if cor)


def de_texto(linhas, cores):
    """Monta uma Grade a partir de linhas de texto; '.' é transparente."""
    g = Grade(len(linhas[0]), len(linhas))
    for y, linha in enumerate(linhas):
        for x, ch in enumerate(linha):
            if ch != ".":
                g.ponto(x, y, cores[ch])
    return g


def _espelho(x):
    return LARGURA - 1 - x


# Pontos dos braços medidos no lado esquerdo, relativos ao topo do corpo (t)
_BRACOS = {
    "normal": [(x, y) for x in (2, 3) for y in (3, 4)],
    "cima": [(x, y) for x in (2, 3) for y in (-2, -1, 0, 1)],
    "cima_torto": [(x, y) for x in (1, 2) for y in (-2, -1)] + [(x, y) for x in (2, 3) for y in (0, 1)],
    "nenhum": [],
}

# Pontos do olho esquerdo relativos ao centro do olho (o direito é espelhado)
_OLHOS = {
    "aberto": [(0, 0, PRETO), (0, 1, PRETO)],
    "fechado": [(-1, 1, PRETO), (0, 1, PRETO)],
    "feliz": [(-1, 1, PRETO), (0, 0, PRETO), (1, 1, PRETO)],
    "tonto": [(-1, 0, PRETO), (1, 0, PRETO), (0, 1, PRETO), (-1, 2, PRETO), (1, 2, PRETO)],
    "arregalado": [(-1, 0, BRANCO), (0, 0, PRETO), (-1, 1, PRETO), (0, 1, PRETO)],
}


def clawd(olhos="aberto", braco_esq="normal", braco_dir="normal", pernas="normal",
          dy=0, dx=0, olhar=0, boca=None, bochecha=False, respira=False):
    """Desenha um quadro do Clawd.

    pernas: normal, passoA, passoB (andando), balancoA, balancoB (pendurado)
    dy/dx: desloca o corpo (agachar, esconder, cambalear)
    olhar: -1/+1 desloca as pupilas pros lados
    respira: abaixa uma linha do topo (dormindo)
    """
    g = Grade(LARGURA, ALTURA)
    t = CORPO_TOPO + dy
    base = t + CORPO_ALTURA - 1
    x0, x1 = CORPO_X0 + dx, CORPO_X1 + dx

    # Pernas: da linha abaixo do corpo até o chão da grade
    for i, px in enumerate(PERNAS_X):
        fim = ALTURA - 1
        if (pernas == "passoA" and i in (0, 2)) or (pernas == "passoB" and i in (1, 3)):
            fim -= 1  # perna levantada
        for y in range(base + 1, fim + 1):
            balanco = 0
            if y > base + 1:
                balanco = {"balancoA": -1, "balancoB": 1}.get(pernas, 0)
            g.ponto(px + dx + balanco, y, LARANJA)

    # Corpo com uma linha de sombra embaixo
    g.retangulo(x0, t + (1 if respira else 0), x1, base - 1, LARANJA)
    g.retangulo(x0, base, x1, base, SOMBRA)

    # Braços
    for (bx, by) in _BRACOS[braco_esq]:
        g.ponto(bx + dx, t + by, LARANJA)
    for (bx, by) in _BRACOS[braco_dir]:
        g.ponto(_espelho(bx) + dx, t + by, LARANJA)

    # Olhos
    ey = t + 2
    for (ox, oy, cor) in _OLHOS[olhos]:
        g.ponto(OLHO_X + ox + dx + olhar, ey + oy, cor)
        g.ponto(_espelho(OLHO_X) - ox + dx + olhar, ey + oy, cor)

    # Boca
    if boca == "aberta":
        g.retangulo(10 + dx, t + 5, 11 + dx, t + 6, PRETO)
    elif boca == "fechada":
        g.retangulo(10 + dx, t + 5, 11 + dx, t + 5, SOMBRA)

    if bochecha:
        g.ponto(5 + dx, t + 4, ROSA)
        g.ponto(_espelho(5) + dx, t + 4, ROSA)
    return g


def _escondido(**kw):
    # Só o topo do corpo aparece, como se estivesse atrás da barra de tarefas
    return clawd(dy=ALTURA - 4 - CORPO_TOPO, braco_esq="nenhum", braco_dir="nenhum", **kw)


def _criar_animacoes():
    """nome -> (milissegundos por quadro, lista de quadros)."""
    normal = clawd()
    piscando = clawd(olhos="fechado")
    esc = _escondido()
    return {
        "parado": (300, [normal] * 9 + [piscando]),
        "andando": (140, [clawd(pernas="passoA"), normal, clawd(pernas="passoB"), normal]),
        "dormindo": (900, [clawd(olhos="fechado", dy=2), clawd(olhos="fechado", dy=2, respira=True)]),
        "pendurado": (180, [clawd(braco_esq="cima", braco_dir="cima", pernas="balancoA"),
                            clawd(braco_esq="cima", braco_dir="cima", pernas="balancoB")]),
        "caindo": (110, [clawd(olhos="arregalado", braco_esq="cima", braco_dir="cima"),
                         clawd(olhos="arregalado", braco_esq="cima_torto", braco_dir="cima_torto")]),
        "comendo": (260, [clawd(boca="aberta"), clawd(olhos="fechado", boca="fechada")]),
        "comemorando": (200, [clawd(olhos="feliz", braco_esq="cima", braco_dir="cima", bochecha=True),
                              clawd(olhos="feliz", bochecha=True)]),
        "acenando": (220, [clawd(olhos="feliz", braco_dir="cima"),
                           clawd(olhos="feliz", braco_dir="cima_torto")]),
        "escondido": (400, [esc] * 4 + [_escondido(olhar=-1)] * 3 + [_escondido(olhar=1)] * 3
                      + [_escondido(olhos="fechado")]),
        "tonto": (160, [clawd(olhos="tonto", dx=-1), clawd(olhos="tonto", dx=1)]),
    }


ANIMACOES = _criar_animacoes()

# Efeitos que flutuam em volta dele
_CORES_EFEITO = {"R": "#E8455A", "W": BRANCO, "Y": "#FFD34D", "Z": "#8FB4FF", "M": "#E8B26A"}
EFEITOS = {
    "coracao": de_texto([".RR.RR.",
                         "RWRRRRR",
                         "RRRRRRR",
                         ".RRRRR.",
                         "..RRR..",
                         "...R..."], _CORES_EFEITO),
    "estrela": de_texto(["..Y..",
                         ".YYY.",
                         "YYWYY",
                         ".YYY.",
                         "..Y.."], _CORES_EFEITO),
    "zzz": de_texto(["ZZZZ",
                     "..Z.",
                     ".Z..",
                     "ZZZZ"], _CORES_EFEITO),
    "migalha": de_texto(["M"], _CORES_EFEITO),
}
