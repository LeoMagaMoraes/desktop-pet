"""Clawd provisório em pixel art, desenhado direto no código.

Cada quadro é uma Grade de cores (None = transparente), virada pra direita.
Cada fase de evolução (ovo, filhote, clawd, anciao) tem o seu conjunto.
Quando existirem PNGs em sprites/, eles substituem estes desenhos.
"""

from dataclasses import dataclass
from functools import lru_cache

LARGURA = 22   # colunas da grade
ALTURA = 14    # linhas da grade; os pés ficam na última linha

# Paleta
LARANJA = "#D97757"
SOMBRA = "#B5583B"
PRETO = "#1B1B1B"
BRANCO = "#FFFFFF"
ROSA = "#F4A3A3"
CASCA = "#F3E9D2"
CASCA_SOMBRA = "#D9CBB0"
BARBA = "#F2EEE6"
ARMACAO = "#3A2A20"
FITA = "#8B2E2E"

FASES = ("ovo", "filhote", "clawd", "anciao")


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


@dataclass(frozen=True)
class Forma:
    """Proporções do corpo. Linhas (dy) são contadas a partir do topo do corpo."""
    x0: int              # coluna esquerda do corpo (a direita é o espelho)
    topo: int            # linha do topo do corpo em pé
    altura: int          # linhas do corpo
    pernas_x: tuple      # colunas das 2 pernas da esquerda
    olho_x: int          # coluna do olho esquerdo
    olho_dy: int
    braco_dy: int
    boca_dy: int
    dy_dormindo: int     # quanto ele agacha pra dormir


ADULTO = Forma(x0=4, topo=3, altura=8, pernas_x=(5, 7), olho_x=7,
               olho_dy=2, braco_dy=3, boca_dy=5, dy_dormindo=2)
FILHOTE = Forma(x0=6, topo=6, altura=6, pernas_x=(7, 9), olho_x=8,
                olho_dy=1, braco_dy=2, boca_dy=3, dy_dormindo=1)

# Braços medidos no lado esquerdo: (coluna relativa a x0, linha relativa ao topo).
# None na linha = usa a altura normal do braço (braco_dy).
_BRACOS = {
    "normal": [(dx, None) for dx in (-2, -1)],
    "cima": [(dx, y) for dx in (-2, -1) for y in (-2, -1, 0, 1)],
    "cima_torto": [(dx, y) for dx in (-3, -2) for y in (-2, -1)] + [(dx, y) for dx in (-2, -1) for y in (0, 1)],
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
          dy=0, dx=0, olhar=0, boca=None, bochecha=False, respira=False,
          forma=ADULTO, acessorios=()):
    """Desenha um quadro do Clawd.

    pernas: normal, passoA, passoB (andando), balancoA, balancoB (pendurado)
    dy/dx: desloca o corpo (agachar, esconder, cambalear)
    olhar: -1/+1 desloca as pupilas pros lados
    respira: abaixa uma linha do topo (dormindo)
    acessorios: qualquer combinação de "cartola", "oculos", "barba"
    """
    f = forma
    g = Grade(LARGURA, ALTURA)
    t = f.topo + dy
    base = t + f.altura - 1
    x0, x1 = f.x0 + dx, _espelho(f.x0) + dx
    todas_pernas = (f.pernas_x[0], f.pernas_x[1], _espelho(f.pernas_x[1]), _espelho(f.pernas_x[0]))

    # Pernas: da linha abaixo do corpo até o chão da grade
    for i, px in enumerate(todas_pernas):
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
    for lado, tipo in ((-1, braco_esq), (1, braco_dir)):
        for (bx, by) in _BRACOS[tipo]:
            linhas = (f.braco_dy, f.braco_dy + 1) if by is None else (by,)
            coluna = f.x0 + bx
            for ly in linhas:
                g.ponto((coluna if lado < 0 else _espelho(coluna)) + dx, t + ly, LARANJA)

    if "barba" in acessorios:
        _barba(g, t + f.boca_dy, dx)

    # Boca
    if boca == "aberta":
        g.retangulo(10 + dx, t + f.boca_dy, 11 + dx, t + f.boca_dy + 1, PRETO)
    elif boca == "fechada":
        g.retangulo(10 + dx, t + f.boca_dy, 11 + dx, t + f.boca_dy, SOMBRA)

    # Olhos
    ey = t + f.olho_dy
    for (ox, oy, cor) in _OLHOS[olhos]:
        g.ponto(f.olho_x + ox + dx + olhar, ey + oy, cor)
        g.ponto(_espelho(f.olho_x) - ox + dx + olhar, ey + oy, cor)

    if bochecha:
        g.ponto(f.x0 + 1 + dx, t + f.braco_dy + 1, ROSA)
        g.ponto(_espelho(f.x0 + 1) + dx, t + f.braco_dy + 1, ROSA)

    if "oculos" in acessorios:
        _oculos(g, f, ey, dx)
    if "cartola" in acessorios:
        _cartola(g, f, t, dx)
    return g


def _barba(g, y, dx):
    # Barba branca que desce do queixo e passa entre as perninhas
    for linha, (a, b) in enumerate(((8, 13), (8, 13), (9, 12), (9, 12), (10, 11))):
        g.retangulo(a + dx, y + linha, b + dx, y + linha, BARBA)


def _oculos(g, f, ey, dx):
    # Duas armações finas de 3 colunas em volta dos olhos e a ponte no meio
    for cx in (f.olho_x, _espelho(f.olho_x)):
        x0, x1, y0, y1 = cx - 1 + dx, cx + 1 + dx, ey - 1, ey + 2
        g.retangulo(x0, y0, x1, y0, ARMACAO)
        g.retangulo(x0, y1, x1, y1, ARMACAO)
        g.retangulo(x0, y0, x0, y1, ARMACAO)
        g.retangulo(x1, y0, x1, y1, ARMACAO)
    g.retangulo(f.olho_x + 2 + dx, ey, _espelho(f.olho_x) - 2 + dx, ey, ARMACAO)


def _cartola(g, f, t, dx):
    x0, x1 = f.x0 + 2 + dx, _espelho(f.x0 + 2) + dx
    g.retangulo(x0, t - 1, x1, t - 1, PRETO)                 # aba
    g.retangulo(x0 + 2, t - 3, x1 - 2, t - 2, PRETO)         # copa
    g.retangulo(x0 + 2, t - 2, x1 - 2, t - 2, FITA)          # fita


# --- ovo ---------------------------------------------------------------------

_OVO = ["....CCCC....",
        "..CCCCCCCC..",
        ".CCCCCCCCCS.",
        ".CCCLLCCCCS.",
        "CCCCLLCCCCCS",
        "CCCCCCCCLLCS",
        "CCCCCCCCLLCS",
        "CCLLCCCCCCCS",
        "CCLLCCCCCCCS",
        ".CCCCCCCCCS.",
        "..CCCCCCSS..",
        "....SSSS...."]
_CORES_OVO = {"C": CASCA, "S": CASCA_SOMBRA, "L": LARANJA}
_OVO_X = 5      # coluna onde o ovo começa na grade
_OVO_TOPO = ALTURA - len(_OVO)


def ovo(inclina=0, rachado=0, dy=0):
    """inclina: -1/+1 balança o topo; rachado: 1 = trincado, 2 = abrindo (com olhinhos)."""
    g = Grade(LARGURA, ALTURA)
    meio = len(_OVO) // 2
    abre = 2 if rachado >= 2 else 0
    for y, linha in enumerate(_OVO):
        desloc = inclina if y < meio else 0
        sobe = abre if y < meio else 0
        for x, ch in enumerate(linha):
            if ch != ".":
                g.ponto(_OVO_X + x + desloc, _OVO_TOPO + y + dy - sobe, _CORES_OVO[ch])
    if rachado:
        # Trinca em zigue-zague no meio da casca
        y = _OVO_TOPO + meio + dy
        for i, x in enumerate(range(_OVO_X + 1, _OVO_X + 11)):
            g.ponto(x, y - (i % 2) - abre, PRETO)
    if rachado >= 2:
        # Olhinhos espiando pela fresta
        for x in (_OVO_X + 4, _OVO_X + 7):
            g.ponto(x, _OVO_TOPO + meio + dy - 1, PRETO)
    return g


# --- animações ---------------------------------------------------------------

def _animacoes_clawd(forma, acessorios):
    def c(**kw):
        return clawd(forma=forma, acessorios=acessorios, **kw)

    def esc(**kw):
        # Só o topo do corpo aparece, como se estivesse atrás da barra de tarefas
        return c(dy=ALTURA - 4 - forma.topo, braco_esq="nenhum", braco_dir="nenhum", **kw)

    normal = c()
    escondido = esc()
    dorme = forma.dy_dormindo
    return {
        "parado": (300, [normal] * 9 + [c(olhos="fechado")]),
        "andando": (140, [c(pernas="passoA"), normal, c(pernas="passoB"), normal]),
        "dormindo": (900, [c(olhos="fechado", dy=dorme), c(olhos="fechado", dy=dorme, respira=True)]),
        "pendurado": (180, [c(braco_esq="cima", braco_dir="cima", pernas="balancoA"),
                            c(braco_esq="cima", braco_dir="cima", pernas="balancoB")]),
        "caindo": (110, [c(olhos="arregalado", braco_esq="cima", braco_dir="cima"),
                         c(olhos="arregalado", braco_esq="cima_torto", braco_dir="cima_torto")]),
        "comendo": (260, [c(boca="aberta"), c(olhos="fechado", boca="fechada")]),
        "comemorando": (200, [c(olhos="feliz", braco_esq="cima", braco_dir="cima", bochecha=True),
                              c(olhos="feliz", bochecha=True)]),
        "acenando": (220, [c(olhos="feliz", braco_dir="cima"), c(olhos="feliz", braco_dir="cima_torto")]),
        "escondido": (400, [escondido] * 4 + [esc(olhar=-1)] * 3 + [esc(olhar=1)] * 3
                      + [esc(olhos="fechado")]),
        "tonto": (160, [c(olhos="tonto", dx=-1), c(olhos="tonto", dx=1)]),
        # "Aaa..." com a cabeça pra cima e depois o "tchim!" pra baixo
        "espirrando": (300, [c(olhos="fechado", boca="fechada"), c(olhos="fechado", dy=1, boca="aberta")]),
    }


def _animacoes_ovo():
    parado = ovo()
    balanca = [ovo(inclina=-1), ovo(inclina=1)]
    escondido = ovo(dy=8)
    return {
        "parado": (250, [parado] * 10 + balanca),
        "andando": (250, [parado] * 10 + balanca),
        "dormindo": (1000, [parado]),
        "pendurado": (150, balanca),
        "caindo": (100, balanca),
        "comendo": (200, balanca),
        "comemorando": (150, balanca),
        "acenando": (200, balanca),
        "escondido": (400, [escondido]),
        "tonto": (120, balanca),
        "chocando": (300, [ovo(rachado=1, inclina=-1), ovo(rachado=1, inclina=1),
                           ovo(rachado=2), ovo(rachado=2, inclina=1)]),
    }


@lru_cache(maxsize=None)
def animacoes(fase):
    """nome -> (milissegundos por quadro, lista de quadros) da fase pedida."""
    if fase == "ovo":
        return _animacoes_ovo()
    if fase == "filhote":
        return _animacoes_clawd(FILHOTE, ())
    if fase == "anciao":
        return _animacoes_clawd(ADULTO, ("cartola", "oculos", "barba"))
    return _animacoes_clawd(ADULTO, ())


def medidas(fase):
    """(altura do corpo, meia largura com os braços), em pixels da grade."""
    if fase == "ovo":
        return len(_OVO), len(_OVO[0]) // 2
    f = FILHOTE if fase == "filhote" else ADULTO
    return ALTURA - f.topo, (LARGURA - 2 * f.x0) // 2 + 2


ANIMACOES = animacoes("clawd")

# Efeitos que flutuam em volta dele
_CORES_EFEITO = {"R": "#E8455A", "W": BRANCO, "Y": "#FFD34D", "Z": "#8FB4FF", "M": "#E8B26A",
                 "K": "#2A2A2A", "G": "#C9D6E3", "B": "#BFE6FF", "A": "#7CC4F2"}
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
    "mosca": de_texto(["W.W",
                       "WKW",
                       ".K."], _CORES_EFEITO),
    "bolha": de_texto([".B.",
                       "B.B",
                       ".B."], _CORES_EFEITO),
    "gota": de_texto(["A",
                      "A"], _CORES_EFEITO),
}
