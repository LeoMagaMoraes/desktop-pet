"""Clawd provisório em pixel art, desenhado direto no código.

Cada quadro é uma Grade de cores (None = transparente), virada pra direita.
Cada fase de evolução (ovo, filhote, clawd, anciao) tem o seu conjunto.
Quando existirem PNGs em sprites/, eles substituem estes desenhos.
"""

from dataclasses import dataclass
from functools import lru_cache

LARGURA = 22   # colunas da grade
ALTURA = 16    # linhas da grade; os pés ficam na última linha (sobra espaço em cima pra chapéus)

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
TAMPA = "#9AA0A6"
TAMPA_SOMBRA = "#6B7075"
# Roupas do clima
GALOCHA = "#F2C14E"
REFLEXO = "#6B7A8F"
CACHECOL = "#C8423B"
GORRO = "#3E7CC9"
PIJAMA = "#7E9BD8"
PIJAMA_LISTRA = "#A9BDEA"
GUARDA = "#3E7CC9"
GUARDA_LISTRA = "#8FB4FF"
CABO = "#5A3A22"

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
    pernas_largura: int = 1   # colunas de cada perna


ADULTO = Forma(x0=4, topo=5, altura=8, pernas_x=(5, 7), olho_x=7,
               olho_dy=2, braco_dy=3, boca_dy=5, dy_dormindo=2)
FILHOTE = Forma(x0=6, topo=8, altura=6, pernas_x=(7, 9), olho_x=8,
                olho_dy=1, braco_dy=2, boca_dy=3, dy_dormindo=1)

# Braços medidos no lado esquerdo: (coluna relativa a x0, linha relativa ao topo).
# None na linha = usa a altura normal do braço (braco_dy).
_BRACOS = {
    "normal": [(dx, None) for dx in (-2, -1)],
    "cima": [(dx, y) for dx in (-2, -1) for y in (-2, -1, 0, 1)],
    "cima_torto": [(dx, y) for dx in (-3, -2) for y in (-2, -1)] + [(dx, y) for dx in (-2, -1) for y in (0, 1)],
    "baixo": [(dx, "b") for dx in (-2, -1)],      # uma linha abaixo do normal (digitando)
    "nenhum": [],
}

# Pontos do olho esquerdo relativos ao centro do olho (o direito é espelhado)
_OLHOS = {
    "aberto": [(0, 0, PRETO), (0, 1, PRETO)],
    "fechado": [(-1, 1, PRETO), (0, 1, PRETO)],
    "feliz": [(-1, 1, PRETO), (0, 0, PRETO), (1, 1, PRETO)],
    "tonto": [(-1, 0, PRETO), (1, 0, PRETO), (0, 1, PRETO), (-1, 2, PRETO), (1, 2, PRETO)],
    "arregalado": [(-1, 0, BRANCO), (0, 0, PRETO), (-1, 1, PRETO), (0, 1, PRETO)],
    "concentrado": [(-1, 0, PRETO), (0, 0, PRETO), (0, 1, PRETO)],
    "apertado": [(-1, 0, PRETO), (0, 1, PRETO), (-1, 2, PRETO)],          # > <
    "sonolento": [(-1, 0, SOMBRA), (0, 0, SOMBRA), (-1, 1, PRETO), (0, 1, PRETO)],
}


@dataclass(frozen=True)
class Pele:
    """Cores do corpo de cada bicho."""
    cor: str
    sombra: str
    pernas: str = None       # cor das pernas, se for diferente do corpo (pé de ave)


PELE_CLAWD = Pele(LARANJA, SOMBRA)


def criatura(olhos="aberto", braco_esq="normal", braco_dir="normal", pernas="normal",
             dy=0, dx=0, olhar=0, boca=None, bochecha=False, respira=False,
             forma=ADULTO, acessorios=(), laptop=False, pele=PELE_CLAWD, atras=None, frente=None,
             placa=False):
    """Desenha um quadro de um bicho de corpo quadradinho (o Clawd e os outros pets).

    pernas: normal, passoA, passoB (andando), balancoA, balancoB (pendurado)
    dy/dx: desloca o corpo (agachar, esconder, cambalear)
    olhar: -1/+1 desloca as pupilas pros lados
    respira: abaixa uma linha do topo (dormindo)
    acessorios: "cartola", "oculos", "barba" (ancião), as roupas do clima ("oculos_sol",
                "guarda_chuva", "galochas", "gorro", "cachecol", "pijama"), as das datas especiais
                ("gorro_natal", "chapeu_festa", "chapeu_bruxa", "orelhas_coelho"), as da loja
                ("coroa", "bone", "laco", "flor", "oculos_coracao", "gravata") e o "fone" da música
    placa: segura uma plaquinha em cima da cabeça (o fiscal do git)
    pele: cores do corpo; atras/frente: funções que desenham detalhes do bicho
          (asas e cauda atrás do corpo, barriga e chifres na frente)
    """
    f = forma
    g = Grade(LARGURA, ALTURA)
    t = f.topo + dy
    base = t + f.altura - 1
    x0, x1 = f.x0 + dx, _espelho(f.x0) + dx
    if "guarda_chuva" in acessorios and braco_dir == "normal":
        braco_dir = "cima"          # o braço direito segura o guarda-chuva
    pose = {"braco_esq": braco_esq, "braco_dir": braco_dir, "respira": respira}

    if atras:
        atras(g, f, t, base, dx, pose)

    # Pernas: da linha abaixo do corpo até o chão da grade (o lado direito é o espelho)
    w = f.pernas_largura
    esquerdas = list(f.pernas_x)
    direitas = [_espelho(px + w - 1) for px in reversed(esquerdas)]
    for i, px in enumerate(esquerdas + direitas):
        fim = ALTURA - 1
        if (pernas == "passoA" and i % 2 == 0) or (pernas == "passoB" and i % 2 == 1):
            fim -= 1  # perna levantada
        for y in range(base + 1, fim + 1):
            balanco = 0
            if y > base + 1:
                balanco = {"balancoA": -1, "balancoB": 1}.get(pernas, 0)
            g.retangulo(px + dx + balanco, y, px + dx + balanco + w - 1, y, pele.pernas or pele.cor)
        if "galochas" in acessorios and fim == ALTURA - 1 and base + 1 <= fim:
            # Botinha amarela nas duas últimas linhas, com a pontinha pra frente
            g.retangulo(px + dx, max(base + 1, fim - 1), px + dx + w - 1, fim, GALOCHA)
            g.ponto(px + dx + w, fim, GALOCHA)

    # Corpo com uma linha de sombra embaixo
    g.retangulo(x0, t + (1 if respira else 0), x1, base - 1, pele.cor)
    g.retangulo(x0, base, x1, base, pele.sombra)
    if frente:
        frente(g, f, t, base, dx, pose)
    if "pijama" in acessorios:
        _pijama(g, f, t, base, dx)

    # Braços
    for lado, tipo in ((-1, braco_esq), (1, braco_dir)):
        for (bx, by) in _BRACOS.get(tipo, ()):
            if by is None:
                linhas = (f.braco_dy, f.braco_dy + 1)
            elif by == "b":
                linhas = (f.braco_dy + 1, f.braco_dy + 2)
            else:
                linhas = (by,)
            coluna = f.x0 + bx
            for ly in linhas:
                g.ponto((coluna if lado < 0 else _espelho(coluna)) + dx, t + ly, pele.cor)

    if "barba" in acessorios:
        _barba(g, t + f.boca_dy, dx)

    # Boca
    if boca == "aberta":
        g.retangulo(10 + dx, t + f.boca_dy, 11 + dx, t + f.boca_dy + 1, PRETO)
    elif boca == "fechada":
        g.retangulo(10 + dx, t + f.boca_dy, 11 + dx, t + f.boca_dy, pele.sombra)

    if "cachecol" in acessorios:
        _cachecol(g, f, t, dx)

    # Olhos (a pálpebra do sonolento usa a sombra da pele)
    ey = t + f.olho_dy
    for (ox, oy, cor) in _OLHOS[olhos]:
        cor = pele.sombra if cor == SOMBRA else cor
        g.ponto(f.olho_x + ox + dx + olhar, ey + oy, cor)
        g.ponto(_espelho(f.olho_x) - ox + dx + olhar, ey + oy, cor)

    if braco_esq == "rosto":
        # Facepalm: o bracinho atravessa o rosto e tapa o olho esquerdo
        g.retangulo(f.x0 - 2 + dx, ey, f.olho_x + 1 + dx, ey + 1, pele.sombra)

    if bochecha:
        g.ponto(f.x0 + 1 + dx, t + f.braco_dy + 1, ROSA)
        g.ponto(_espelho(f.x0 + 1) + dx, t + f.braco_dy + 1, ROSA)

    if "gravata" in acessorios and "cachecol" not in acessorios:
        _gravata(g, f, t, dx)
    for nome in OCULOS:                        # só um par de óculos (o primeiro da lista ganha)
        if nome in acessorios:
            _DESENHO_OCULOS[nome](g, f, ey, dx)
            break
    chapeu = next((nome for nome in CHAPEUS if nome in acessorios), None)   # só um chapéu
    if chapeu:
        _DESENHO_CHAPEU[chapeu](g, f, t, dx)
    if "fone" in acessorios:
        _fone(g, f, t, ey, dx, com_chapeu=chapeu is not None)
    if "guarda_chuva" in acessorios:
        _guarda_chuva(g, f, t, dx)
    if laptop:
        _laptop(g, f, t)
    if placa:
        _placa(g, f, t, dx)
    return g


def clawd(**kw):
    """Um quadro do Clawd (a criatura com a pele laranja e sem detalhes extras)."""
    return criatura(**kw)


def _oculos_sol(g, f, ey, dx):
    # Lentes pretas de 3x2 com um reflexo, ligadas por uma ponte
    for cx in (f.olho_x, _espelho(f.olho_x)):
        g.retangulo(cx - 1 + dx, ey, cx + 1 + dx, ey + 1, PRETO)
        g.ponto(cx + dx, ey, REFLEXO)
    g.retangulo(f.olho_x + 2 + dx, ey, _espelho(f.olho_x) - 2 + dx, ey, PRETO)


def _cachecol(g, f, t, dx):
    # Faixa grossa listrada na altura da boca e a ponta caindo pra fora do lado esquerdo
    y = t + f.boca_dy
    for x in range(f.x0 + dx, _espelho(f.x0) + dx + 1):
        cor = BARBA if (x - f.x0) % 3 == 2 else CACHECOL
        g.ponto(x, y, cor)
        g.ponto(x, y + 1, cor)
    for i, yy in enumerate(range(y + 1, y + 5)):
        g.retangulo(f.x0 - 1 + dx, yy, f.x0 + dx, yy, BARBA if i % 2 else CACHECOL)


def _gorro(g, f, t, dx):
    # Gorro azul com barra branca e pompom
    x0, x1 = f.x0 + 1 + dx, _espelho(f.x0 + 1) + dx
    g.retangulo(x0, t - 1, x1, t - 1, BARBA)
    g.retangulo(x0 + 1, t - 2, x1 - 1, t - 2, GORRO)
    g.retangulo(x0 + 3, t - 3, x1 - 3, t - 3, GORRO)
    meio = LARGURA // 2 + dx
    g.retangulo(meio - 1, t - 3, meio, t - 3, BARBA)


def _pijama(g, f, t, base, dx):
    # Do meio do corpo pra baixo vira um pijama listrado
    for y in range(t + f.braco_dy, base):
        for x in range(f.x0 + dx, _espelho(f.x0) + dx + 1):
            g.ponto(x, y, PIJAMA_LISTRA if (x - f.x0) % 3 == 0 else PIJAMA)


def _touca(g, f, t, dx):
    # Touca de dormir caída pro lado, com pompom
    x0, x1 = f.x0 + 2 + dx, _espelho(f.x0 + 2) + dx
    g.retangulo(x0, t - 1, x1, t - 1, PIJAMA)
    g.retangulo(x0 + 2, t - 2, x1 + 1, t - 2, PIJAMA)
    g.retangulo(x1 - 1, t - 3, x1 + 2, t - 3, PIJAMA_LISTRA)
    g.ponto(x1 + 3, t - 3, BRANCO)


def _guarda_chuva(g, f, t, dx):
    # Copa listrada bem acima da cabeça e o cabo descendo até a mão direita levantada
    centro = _espelho(f.x0) + dx                       # coluna do lado de dentro do braço direito
    for y, meia in ((t - 5, 3), (t - 4, 5), (t - 3, 6)):
        for x in range(centro - meia, centro + meia + 1):
            g.ponto(x, y, GUARDA if ((x - centro + 1) // 2) % 2 == 0 else GUARDA_LISTRA)
    for x in range(centro - 6, centro + 7, 2):          # beirada ondulada
        g.ponto(x, t - 2, GUARDA)
    g.retangulo(centro, t - 2, centro, t - 1, CABO)     # cabo
    g.ponto(centro, t - 6, TAMPA_SOMBRA)                 # pontinha


def _laptop(g, f, t):
    # Tampa de laptop vista de trás, no chão na frente dele, com um brilhinho no meio
    meia = (LARGURA - 2 * f.x0) // 4 + 1
    x0, x1 = LARGURA // 2 - meia, LARGURA // 2 - 1 + meia
    topo = t + f.olho_dy + 2
    g.retangulo(x0, topo, x1, ALTURA - 2, TAMPA)
    g.retangulo(x0, ALTURA - 1, x1, ALTURA - 1, TAMPA_SOMBRA)
    g.ponto(LARGURA // 2 - 1, (topo + ALTURA - 1) // 2, BRANCO)


def _placa(g, f, t, dx):
    # Plaquinha clara erguida acima da cabeça, com "letrinhas" (o balão diz o que está escrito)
    x0, x1 = f.x0 - 2 + dx, _espelho(f.x0 - 2) + dx
    g.retangulo(x0, t - 5, x1, t - 3, CASCA)
    g.retangulo(x0, t - 3, x1, t - 3, CASCA_SOMBRA)
    for x in range(x0 + 1, x1):
        if (x - x0) % 4 != 0:
            g.ponto(x, t - 4, PRETO)


def de_cabeca_pra_baixo(grade, descer):
    """Vira a grade de ponta-cabeça e desce `descer` linhas (pra encostar no chão)."""
    g = Grade(grade.largura, grade.altura)
    for y, linha in enumerate(grade.px):
        for x, cor in enumerate(linha):
            if cor:
                g.ponto(x, grade.altura - 1 - y + descer, cor)
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


# --- datas especiais, loja e música -------------------------------------------

VERMELHO_NATAL = "#D93A3A"
FESTA = ("#F06292", "#4FC3F7", "#FFD34D")
BRUXA = "#4B2C6B"
BRUXA_FAIXA = "#F28C28"
COELHO = "#F4F1EA"
OURO = "#F2C14E"
OURO_SOMBRA = "#C99A2E"
RUBI = "#E8455A"
BONE = "#3E7CC9"
BONE_ABA = "#2C5E9E"
LACO = "#F06292"
LACO_NO = "#C2185B"
GRAVATA = "#C8423B"
GRAVATA_NO = "#8B2E2E"
FONE = "#9AA0A6"
FONE_COR = "#4FC3F7"


def _gorro_natal(g, f, t, dx):
    # Gorro vermelho caído pro lado, barra branca e pompom
    x0, x1 = f.x0 + 1 + dx, _espelho(f.x0 + 1) + dx
    g.retangulo(x0, t - 1, x1, t - 1, BRANCO)
    g.retangulo(x0 + 1, t - 2, x1 - 1, t - 2, VERMELHO_NATAL)
    g.retangulo(x0 + 3, t - 3, x1 - 1, t - 3, VERMELHO_NATAL)
    g.retangulo(x1 - 2, t - 4, x1, t - 4, VERMELHO_NATAL)
    g.retangulo(x1 + 1, t - 4, x1 + 2, t - 3, BRANCO)


def _chapeu_festa(g, f, t, dx):
    # Cone listrado no meio da cabeça com uma bolinha em cima
    meio = LARGURA // 2 + dx
    for i, (y, meia) in enumerate(((t - 1, 2), (t - 2, 2), (t - 3, 1), (t - 4, 1))):
        g.retangulo(meio - meia, y, meio + meia - 1, y, FESTA[i % 3])
    g.retangulo(meio - 1, t - 5, meio, t - 5, FESTA[2])


def _chapeu_bruxa(g, f, t, dx):
    # Aba larga, faixa laranja e a ponta entortada pro lado
    x0, x1 = f.x0 + dx, _espelho(f.x0) + dx
    meio = LARGURA // 2 + dx
    g.retangulo(x0, t - 1, x1, t - 1, BRUXA)
    g.retangulo(meio - 3, t - 2, meio + 2, t - 2, BRUXA_FAIXA)
    g.retangulo(meio - 2, t - 3, meio + 1, t - 3, BRUXA)
    g.retangulo(meio - 1, t - 4, meio + 1, t - 4, BRUXA)
    g.retangulo(meio + 1, t - 5, meio + 2, t - 5, BRUXA)


def _orelhas_coelho(g, f, t, dx):
    # Tiara com duas orelhonas brancas, rosinhas por dentro
    meio = LARGURA // 2 + dx
    g.retangulo(f.x0 + 1 + dx, t - 1, _espelho(f.x0 + 1) + dx, t - 1, COELHO)
    for ex in (meio - 4, meio + 2):
        g.retangulo(ex, t - 5, ex + 1, t - 2, COELHO)
        g.retangulo(ex + (1 if ex < meio else 0), t - 4, ex + (1 if ex < meio else 0), t - 2, ROSA)


def _coroa(g, f, t, dx):
    # Coroa dourada com três pontas e rubis
    meio = LARGURA // 2 + dx
    g.retangulo(meio - 3, t - 1, meio + 2, t - 1, OURO)
    for px in (meio - 3, meio - 1, meio, meio + 2):
        g.ponto(px, t - 2, OURO)
    g.ponto(meio - 3, t - 3, OURO)
    g.ponto(meio + 2, t - 3, OURO)
    g.retangulo(meio - 1, t - 3, meio, t - 3, OURO_SOMBRA)
    g.ponto(meio - 2, t - 1, RUBI)
    g.ponto(meio + 1, t - 1, RUBI)


def _bone(g, f, t, dx):
    # Boné azul com a aba pra frente (pro lado em que ele olha)
    x0, x1 = f.x0 + 1 + dx, _espelho(f.x0 + 1) + dx
    g.retangulo(x0, t - 1, x1, t - 1, BONE)
    g.retangulo(x0 + 2, t - 2, x1 - 2, t - 2, BONE)
    g.retangulo(x1 + 1, t - 1, x1 + 3, t - 1, BONE_ABA)
    g.ponto(LARGURA // 2 + dx, t - 3, BONE_ABA)


def _laco(g, f, t, dx):
    # Laço rosa no cantinho da cabeça
    cx = _espelho(f.x0 + 3) + dx
    for y in (t - 2, t - 1):
        g.retangulo(cx - 2, y, cx - 1, y, LACO)
        g.retangulo(cx + 1, y, cx + 2, y, LACO)
    g.ponto(cx, t - 2, LACO_NO)
    g.ponto(cx, t - 1, LACO_NO)


def _flor(g, f, t, dx):
    # Florzinha branca de miolo amarelo atrás da "orelha"
    cx = _espelho(f.x0 + 2) + dx
    for px, py in ((cx - 1, t - 2), (cx + 1, t - 2), (cx, t - 3), (cx, t - 1)):
        g.ponto(px, py, BRANCO)
    g.ponto(cx, t - 2, "#FFD34D")


def _oculos_coracao(g, f, ey, dx):
    # Um coraçãozinho vermelho em cada olho
    for cx in (f.olho_x, _espelho(f.olho_x)):
        cx += dx
        g.ponto(cx - 1, ey - 1, RUBI)
        g.ponto(cx + 1, ey - 1, RUBI)
        g.retangulo(cx - 1, ey, cx + 1, ey, RUBI)
        g.ponto(cx, ey + 1, RUBI)
    g.retangulo(f.olho_x + 2 + dx, ey, _espelho(f.olho_x) - 2 + dx, ey, GRAVATA_NO)


def _gravata(g, f, t, dx):
    # Gravata-borboleta logo abaixo da boca
    meio = LARGURA // 2 + dx
    y = t + f.boca_dy + 1
    g.retangulo(meio - 3, y, meio - 2, y, GRAVATA)
    g.retangulo(meio + 1, y, meio + 2, y, GRAVATA)
    g.retangulo(meio - 1, y, meio, y, GRAVATA_NO)
    g.ponto(meio - 3, y - 1, GRAVATA)
    g.ponto(meio + 2, y - 1, GRAVATA)
    g.ponto(meio - 3, y + 1, GRAVATA)
    g.ponto(meio + 2, y + 1, GRAVATA)


def _fone(g, f, t, ey, dx, com_chapeu=False):
    # Conchas coloridas de 2 colunas dos lados da cabeça e o arco por cima (some embaixo do chapéu)
    for lado in (-1, 1):
        x = f.x0 - 2 if lado < 0 else _espelho(f.x0 - 1)
        g.retangulo(x + dx, ey - 1, x + 1 + dx, ey + 1, FONE_COR)
        g.retangulo(x + dx, ey - 1, x + 1 + dx, ey - 1, FONE)
        arco = f.x0 - 1 if lado < 0 else _espelho(f.x0 - 1)
        g.retangulo(arco + dx, t - 1, arco + dx, ey - 2, FONE)
    if not com_chapeu:
        g.retangulo(f.x0 + dx, t - 1, _espelho(f.x0) + dx, t - 1, FONE)


# Ordem de preferência quando tem mais de um: data especial > clima > loja > fase (ancião)
CHAPEUS = ("gorro_natal", "chapeu_bruxa", "orelhas_coelho", "chapeu_festa", "gorro", "pijama",
           "coroa", "bone", "laco", "flor", "cartola")
_DESENHO_CHAPEU = {"gorro_natal": _gorro_natal, "chapeu_bruxa": _chapeu_bruxa, "orelhas_coelho": _orelhas_coelho,
                   "chapeu_festa": _chapeu_festa, "gorro": _gorro, "pijama": _touca, "coroa": _coroa,
                   "bone": _bone, "laco": _laco, "flor": _flor, "cartola": _cartola}
OCULOS = ("oculos_sol", "oculos_coracao", "oculos")
_DESENHO_OCULOS = {"oculos_sol": _oculos_sol, "oculos_coracao": _oculos_coracao, "oculos": _oculos}


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


def ovo(inclina=0, rachado=0, dy=0, cores=None):
    """inclina: -1/+1 balança o topo; rachado: 1 = trincado, 2 = abrindo (com olhinhos)."""
    g = Grade(LARGURA, ALTURA)
    meio = len(_OVO) // 2
    abre = 2 if rachado >= 2 else 0
    for y, linha in enumerate(_OVO):
        desloc = inclina if y < meio else 0
        sobe = abre if y < meio else 0
        for x, ch in enumerate(linha):
            if ch != ".":
                g.ponto(_OVO_X + x + desloc, _OVO_TOPO + y + dy - sobe, (cores or _CORES_OVO)[ch])
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


_desenhar_ovo = ovo     # apelido: dentro de _animacoes_ovo o nome "ovo" é a versão com as cores do bicho


# --- dragãozinho ---------------------------------------------------------------

VERDE = "#5DAE6B"
VERDE_SOMBRA = "#3E8A50"
BARRIGA = "#F2D98B"
CHIFRE = "#F2E6C9"
ASA = "#9FDCA9"
NARINA = "#2E6B3C"

PELE_DRAGAO = Pele(VERDE, VERDE_SOMBRA)
DRAGAO_ADULTO = Forma(x0=5, topo=5, altura=8, pernas_x=(7,), olho_x=8, olho_dy=2,
                      braco_dy=4, boca_dy=5, dy_dormindo=2, pernas_largura=2)
DRAGAO_FILHOTE = Forma(x0=7, topo=8, altura=6, pernas_x=(8,), olho_x=9, olho_dy=1,
                       braco_dy=3, boca_dy=4, dy_dormindo=1, pernas_largura=2)

# Asa esquerda (coluna relativa a x0, linha relativa ao topo); a direita é o espelho
_ASA = [(-4, -2), (-4, -1), (-3, -1), (-4, 0), (-3, 0), (-2, 0), (-3, 1), (-2, 1), (-1, 1), (-2, 2), (-1, 2)]
_ASA_PEQUENA = [(-3, 0), (-3, 1), (-2, 1), (-2, 2), (-1, 2)]
# Cauda do lado direito (coluna depois do corpo, linha relativa à base) e a pontinha
_CAUDA = [(1, 0), (2, 0), (3, -1), (4, -2)], (4, -3)
_CAUDA_PEQUENA = [(1, 0), (2, -1)], (3, -2)


def _dragao_atras(g, f, t, base, dx, pose):
    """Asas (sobem quando ele levanta os braços) e a cauda com espinho."""
    pequeno = f.altura < 8
    erguidas = pose["braco_esq"] in ("cima", "cima_torto") or pose["braco_dir"] in ("cima", "cima_torto")
    sobe = 1 if erguidas else 0
    asa = _ASA_PEQUENA if pequeno else _ASA
    borda = min(wx for wx, _ in asa)
    for wx, wy in asa:
        cor = VERDE_SOMBRA if wx == borda else ASA
        g.ponto(f.x0 + wx + dx, t + wy - sobe, cor)
        g.ponto(_espelho(f.x0 + wx) + dx, t + wy - sobe, cor)
    pontos, ponta = _CAUDA_PEQUENA if pequeno else _CAUDA
    x1 = _espelho(f.x0) + dx
    for cx, cy in pontos:
        g.ponto(x1 + cx, base + cy, VERDE)
    g.ponto(x1 + ponta[0], base + ponta[1], CHIFRE)


def _dragao_frente(g, f, t, base, dx, pose):
    """Barriga clarinha, narinas, chifres e a crista."""
    pequeno = f.altura < 8
    meia = 2 if pequeno else 3
    centro = LARGURA // 2
    g.retangulo(centro - meia + dx, t + f.boca_dy, centro + meia - 1 + dx, base - 1, BARRIGA)
    narinas = (centro - 1, centro) if pequeno else (centro - 2, centro + 1)
    for nx in narinas:
        g.ponto(nx + dx, t + f.olho_dy + 2, NARINA)
    chifres = [(1, -1)] if pequeno else [(1, -1), (0, -2)]
    for cx, cy in chifres:
        g.ponto(f.x0 + cx + dx, t + cy, CHIFRE)
        g.ponto(_espelho(f.x0 + cx) + dx, t + cy, CHIFRE)
    if not pequeno:
        g.retangulo(centro - 1 + dx, t - 1, centro + dx, t - 1, VERDE_SOMBRA)   # crista


def dragao(**kw):
    """Um quadro do dragãozinho: a mesma criatura, com pele verde, asas, cauda e chifres."""
    return criatura(pele=PELE_DRAGAO, atras=_dragao_atras, frente=_dragao_frente, **kw)


_CORES_OVO_DRAGAO = {"C": "#A8DDB0", "S": "#6FB27B", "L": VERDE_SOMBRA}

# --- tubarãozinho --------------------------------------------------------------

AZUL_TUBARAO = "#6F9FCB"
AZUL_TUBARAO_SOMBRA = "#4F7DA8"
BARRIGA_TUBARAO = "#EAF2F8"
GUELRA = "#3D6489"

PELE_TUBARAO = Pele(AZUL_TUBARAO, AZUL_TUBARAO_SOMBRA)

# Cauda em meia-lua do lado direito (coluna depois do corpo, linha relativa à base)
_RABO = [(1, -1), (2, -2), (3, -3), (3, -4), (2, 0), (3, 0)]
_RABO_PEQUENO = [(1, -1), (2, -2), (2, 0)]


def _tubarao_atras(g, f, t, base, dx, pose):
    """Cauda em meia-lua atrás do corpo."""
    x1 = _espelho(f.x0) + dx
    for cx, cy in (_RABO_PEQUENO if f.altura < 8 else _RABO):
        g.ponto(x1 + cx, base + cy, AZUL_TUBARAO_SOMBRA)


def _tubarao_frente(g, f, t, base, dx, pose):
    """Barriga branca, sorriso de dentinhos, guelras e a barbatana das costas."""
    pequeno = f.altura < 8
    centro = LARGURA // 2
    meia = 2 if pequeno else 3
    boca = t + f.boca_dy
    g.retangulo(f.x0 + 1 + dx, boca + 1, _espelho(f.x0 + 1) + dx, base - 1, BARRIGA_TUBARAO)
    # Sorriso: linha escura com dentinhos brancos alternados
    for i, x in enumerate(range(centro - meia, centro + meia)):
        g.ponto(x + dx, boca, BRANCO if i % 2 else PRETO)
    # Guelras dos dois lados
    for y in (t + f.olho_dy + 1, t + f.olho_dy + 2):
        g.ponto(f.x0 + 1 + dx, y, GUELRA)
        g.ponto(_espelho(f.x0 + 1) + dx, y, GUELRA)
    # Barbatana nas costas, inclinada pra trás
    if pequeno:
        g.retangulo(centro - 1 + dx, t - 1, centro + dx, t - 1, AZUL_TUBARAO_SOMBRA)
        g.ponto(centro + dx, t - 2, AZUL_TUBARAO_SOMBRA)
    else:
        g.retangulo(centro - 2 + dx, t - 1, centro + 1 + dx, t - 1, AZUL_TUBARAO_SOMBRA)
        g.retangulo(centro - 1 + dx, t - 2, centro + dx, t - 2, AZUL_TUBARAO_SOMBRA)
        g.ponto(centro + dx, t - 3, AZUL_TUBARAO_SOMBRA)


def tubarao(**kw):
    """Um quadro do tubarãozinho."""
    return criatura(pele=PELE_TUBARAO, atras=_tubarao_atras, frente=_tubarao_frente, **kw)


# Ovo de tubarão é uma cápsula marrom ("bolsa de sereia")
_CORES_OVO_TUBARAO = {"C": "#8C6A4F", "S": "#5E4634", "L": "#B08D6E"}


# --- pinguinzinho --------------------------------------------------------------

PINGUIM = "#2F3742"
PINGUIM_SOMBRA = "#1E242C"
BRANCO_PINGUIM = "#F4F6F8"
LARANJA_BICO = "#F2A03D"

PELE_PINGUIM = Pele(PINGUIM, PINGUIM_SOMBRA, pernas=LARANJA_BICO)


def _pinguim_frente(g, f, t, base, dx, pose):
    """Rosto e barriga brancos, com o biquinho laranja."""
    g.retangulo(f.x0 + 2 + dx, t + 1, _espelho(f.x0 + 2) + dx, base - 1, BRANCO_PINGUIM)
    centro = LARGURA // 2
    g.retangulo(centro - 1 + dx, t + f.olho_dy + 2, centro + dx, t + f.olho_dy + 2, LARANJA_BICO)


_CORES_OVO_PINGUIM = {"C": "#EEF2F5", "S": "#C9D3DC", "L": "#9FB1C2"}


# --- patinho de borracha -------------------------------------------------------

PATO = "#F7D33C"
PATO_SOMBRA = "#DDAE1F"
BICO_PATO = "#F28C28"
BICO_PATO_SOMBRA = "#D9731A"

PELE_PATO = Pele(PATO, PATO_SOMBRA, pernas=BICO_PATO)


def _pato_atras(g, f, t, base, dx, pose):
    """Rabinho arrebitado do lado direito."""
    x1 = _espelho(f.x0) + dx
    g.ponto(x1 + 1, base - 1, PATO)
    g.ponto(x1 + 2, base - 2, PATO)
    if f.altura >= 8:
        g.ponto(x1 + 2, base - 3, PATO)


def _pato_frente(g, f, t, base, dx, pose):
    """Bicão laranja e um topetinho enrolado."""
    centro = LARGURA // 2
    meia = 1 if f.altura < 8 else 2
    y = t + f.olho_dy + 2
    g.retangulo(centro - meia + dx, y, centro + meia - 1 + dx, y, BICO_PATO)
    g.retangulo(centro - meia + dx, y + 1, centro + meia - 1 + dx, y + 1, BICO_PATO_SOMBRA)
    g.ponto(centro - 1 + dx, t - 1, PATO)
    g.ponto(centro + dx, t - 1, PATO)
    g.ponto(centro + dx, t - 2, PATO)


_CORES_OVO_PATO = {"C": "#FFF4C2", "S": "#E8D486", "L": "#E8C547"}


# --- fênix ---------------------------------------------------------------------

FENIX = "#E2543B"
FENIX_SOMBRA = "#B13A26"
CHAMA = "#F28C28"
CHAMA_CLARA = "#FFD34D"

PELE_FENIX = Pele(FENIX, FENIX_SOMBRA, pernas=CHAMA_CLARA)


def _fenix_atras(g, f, t, base, dx, pose):
    """Asas de fogo (sobem com os braços) e a cauda em chamas."""
    pequeno = f.altura < 8
    erguidas = pose["braco_esq"] in ("cima", "cima_torto") or pose["braco_dir"] in ("cima", "cima_torto")
    sobe = 1 if erguidas else 0
    asa = _ASA_PEQUENA if pequeno else _ASA
    borda = min(wx for wx, _ in asa)
    for wx, wy in asa:
        cor = CHAMA_CLARA if wx == borda else CHAMA
        g.ponto(f.x0 + wx + dx, t + wy - sobe, cor)
        g.ponto(_espelho(f.x0 + wx) + dx, t + wy - sobe, cor)
    x1 = _espelho(f.x0) + dx
    cauda = [(1, 0), (2, -1), (3, -2)] if pequeno else [(1, 0), (2, 0), (2, -1), (3, -2), (3, -3)]
    for cx, cy in cauda:
        g.ponto(x1 + cx, base + cy, CHAMA)
    ponta = (4, -3) if pequeno else (4, -4)
    g.ponto(x1 + ponta[0], base + ponta[1], CHAMA_CLARA)


def _fenix_frente(g, f, t, base, dx, pose):
    """Peito dourado, biquinho e a crista de fogo."""
    pequeno = f.altura < 8
    centro = LARGURA // 2
    meia = 2 if pequeno else 3
    g.retangulo(centro - meia + dx, t + f.boca_dy, centro + meia - 1 + dx, base - 1, CHAMA_CLARA)
    g.retangulo(centro - 1 + dx, t + f.olho_dy + 2, centro + dx, t + f.olho_dy + 2, CHAMA_CLARA)
    crista = [(-1, -1, CHAMA_CLARA), (0, -1, CHAMA), (1, -1, CHAMA), (0, -2, CHAMA_CLARA)]
    if not pequeno:
        crista += [(-2, -1, CHAMA), (2, -1, CHAMA_CLARA), (1, -2, CHAMA), (1, -3, CHAMA_CLARA)]
    for cx, cy, cor in crista:
        g.ponto(centro + cx - 1 + dx, t + cy, cor)


_CORES_OVO_FENIX = {"C": "#F28C28", "S": "#C2581C", "L": "#FFD34D"}


# --- corujinha -----------------------------------------------------------------

CORUJA = "#8B6A4E"
CORUJA_SOMBRA = "#6B4F3A"
DISCO = "#F2E6C9"
PEITO_CORUJA = "#D9C3A5"
BICO_CORUJA = "#E8B23B"

PELE_CORUJA = Pele(CORUJA, CORUJA_SOMBRA, pernas=BICO_CORUJA)


def _coruja_frente(g, f, t, base, dx, pose):
    """Discos claros em volta dos olhos, biquinho, peito pintadinho e as orelhinhas de pena."""
    centro = LARGURA // 2
    ey = t + f.olho_dy
    for cx in (f.olho_x, _espelho(f.olho_x)):
        g.retangulo(cx - 1 + dx, ey - 1, cx + 1 + dx, ey + 2, DISCO)
    g.ponto(centro - 1 + dx, ey + 2, BICO_CORUJA)
    g.ponto(centro + dx, ey + 2, BICO_CORUJA)
    if f.altura >= 8:
        g.retangulo(centro - 3 + dx, t + f.boca_dy, centro + 2 + dx, base - 1, PEITO_CORUJA)
        for px, py in ((centro - 2, t + f.boca_dy), (centro + 1, t + f.boca_dy), (centro - 1, base - 1)):
            g.ponto(px + dx, py, CORUJA_SOMBRA)
    tufos = [(0, -1), (0, -2), (1, -1)] if f.altura >= 8 else [(0, -1)]
    for tx, ty in tufos:
        g.ponto(f.x0 + tx + dx, t + ty, CORUJA_SOMBRA)
        g.ponto(_espelho(f.x0 + tx) + dx, t + ty, CORUJA_SOMBRA)


_CORES_OVO_CORUJA = {"C": "#F4F1EA", "S": "#D8D0C0", "L": "#B39A7C"}


# --- porquinho-da-índia --------------------------------------------------------

PORQUINHO = "#D9A066"
PORQUINHO_SOMBRA = "#B07D45"
PELO_BRANCO = "#F5EDE0"
PELO_ESCURO = "#6B4A2E"
NARIZ_ROSA = "#E89AA6"
PE_ROSA = "#E8B0A0"
FENO = "#E8D28A"

PELE_PORQUINHO = Pele(PORQUINHO, PORQUINHO_SOMBRA, pernas=PE_ROSA)
# Mais largo e mais baixinho que os outros, com perninhas curtas
PORQUINHO_ADULTO = Forma(x0=4, topo=6, altura=8, pernas_x=(6,), olho_x=7, olho_dy=2,
                         braco_dy=4, boca_dy=5, dy_dormindo=1, pernas_largura=2)
PORQUINHO_FILHOTE = Forma(x0=6, topo=9, altura=5, pernas_x=(7,), olho_x=8, olho_dy=1,
                          braco_dy=2, boca_dy=3, dy_dormindo=1, pernas_largura=2)


def _porquinho_frente(g, f, t, base, dx, pose):
    """Pelo tricolor: mancha escura de um lado, faixa branca no rosto, focinho e barriga brancos,
    nariz rosa e orelhinhas redondas."""
    pequeno = f.altura < 8
    centro = LARGURA // 2
    x1 = _espelho(f.x0)
    # Mancha marrom-escura no alto do lado esquerdo
    g.retangulo(f.x0 + dx, t, f.x0 + (2 if pequeno else 3) + dx, t + (1 if pequeno else 2), PELO_ESCURO)
    # Faixa branca descendo pela testa até o focinho
    g.retangulo(centro - 1 + dx, t, centro + dx, t + f.olho_dy + 2, PELO_BRANCO)
    g.retangulo(centro - 2 + dx, t + f.olho_dy + 2, centro + 1 + dx, t + f.olho_dy + 3, PELO_BRANCO)
    # Barriguinha branca
    g.retangulo(f.x0 + 3 + dx, base - (1 if pequeno else 2), x1 - 3 + dx, base - 1, PELO_BRANCO)
    # Nariz rosa
    g.retangulo(centro - 1 + dx, t + f.olho_dy + 2, centro + dx, t + f.olho_dy + 2, NARIZ_ROSA)
    # Orelhinhas redondas (rosinha por dentro)
    for lado in (-1, 1):
        ox = f.x0 + 1 if lado < 0 else _espelho(f.x0 + 1)
        g.ponto(ox + dx, t - 1, PORQUINHO_SOMBRA)
        g.ponto(ox + (1 if lado < 0 else -1) + dx, t - 1, NARIZ_ROSA)


# Porquinho-da-índia não sai de ovo: começa num ninho de feno
_CORES_OVO_PORQUINHO = {"C": FENO, "S": "#C9AE5B", "L": "#A88A3D"}


# --- coala ---------------------------------------------------------------------

COALA = "#9AA3AB"
COALA_SOMBRA = "#7A838C"
COALA_CLARO = "#E8E3DC"
NARIZ_COALA = "#3A3A40"

PELE_COALA = Pele(COALA, COALA_SOMBRA)
COALA_ADULTO = Forma(x0=5, topo=6, altura=8, pernas_x=(7,), olho_x=7, olho_dy=2,
                     braco_dy=4, boca_dy=6, dy_dormindo=1, pernas_largura=2)
COALA_FILHOTE = Forma(x0=7, topo=9, altura=5, pernas_x=(8,), olho_x=8, olho_dy=1,
                      braco_dy=2, boca_dy=3, dy_dormindo=1, pernas_largura=2)


def _coala_frente(g, f, t, base, dx, pose):
    """Orelhonas redondas (clarinhas por dentro), narizão escuro e queixo/barriga claros."""
    pequeno = f.altura < 8
    centro = LARGURA // 2
    ey = t + f.olho_dy
    # Queixo e barriga clarinhos
    g.retangulo(f.x0 + 2 + dx, t + f.boca_dy, _espelho(f.x0 + 2) + dx, base - 1, COALA_CLARO)
    # Narizão: mais largo em cima, afinando embaixo
    if pequeno:
        g.retangulo(centro - 1 + dx, ey + 1, centro + dx, ey + 2, NARIZ_COALA)
    else:
        g.retangulo(centro - 2 + dx, ey + 1, centro + 1 + dx, ey + 2, NARIZ_COALA)
        g.retangulo(centro - 1 + dx, ey + 3, centro + dx, ey + 3, NARIZ_COALA)
    # Orelhonas nos cantos de cima, saindo pra fora da cabeça
    tamanho = 3 if pequeno else 4
    for lado in (-1, 1):
        for oy in range(tamanho):
            for ox in range(tamanho):
                canto = oy == 0 and ox in (0, tamanho - 1)       # cantinho arredondado
                if canto:
                    continue
                x = f.x0 - 2 + ox if lado < 0 else _espelho(f.x0 - 2 + ox)
                dentro = 0 < ox < tamanho - 1 and 0 < oy < tamanho - 1 or (pequeno and ox == 1 and oy == 1)
                g.ponto(x + dx, t - tamanho + 1 + oy, COALA_CLARO if dentro else COALA)


# Coala é marsupial: começa na bolsinha da mamãe
_CORES_OVO_COALA = {"C": "#A89580", "S": "#7E6D5A", "L": "#C9B8A3"}


# Como desenhar cada bicho: proporções do filhote e do adulto, estilo e cores do ovo
BICHOS = {
    "clawd": {"filhote": FILHOTE, "adulto": ADULTO, "estilo": {}, "ovo": _CORES_OVO},
    "dragao": {"filhote": DRAGAO_FILHOTE, "adulto": DRAGAO_ADULTO,
               "estilo": {"pele": PELE_DRAGAO, "atras": _dragao_atras, "frente": _dragao_frente},
               "ovo": _CORES_OVO_DRAGAO},
    "tubarao": {"filhote": DRAGAO_FILHOTE, "adulto": DRAGAO_ADULTO,      # mesmas proporções do dragão
                "estilo": {"pele": PELE_TUBARAO, "atras": _tubarao_atras, "frente": _tubarao_frente},
                "ovo": _CORES_OVO_TUBARAO},
    "pinguim": {"filhote": DRAGAO_FILHOTE, "adulto": DRAGAO_ADULTO,
                "estilo": {"pele": PELE_PINGUIM, "frente": _pinguim_frente}, "ovo": _CORES_OVO_PINGUIM},
    "pato": {"filhote": DRAGAO_FILHOTE, "adulto": DRAGAO_ADULTO,
             "estilo": {"pele": PELE_PATO, "atras": _pato_atras, "frente": _pato_frente}, "ovo": _CORES_OVO_PATO},
    "fenix": {"filhote": DRAGAO_FILHOTE, "adulto": DRAGAO_ADULTO,
              "estilo": {"pele": PELE_FENIX, "atras": _fenix_atras, "frente": _fenix_frente},
              "ovo": _CORES_OVO_FENIX},
    "coruja": {"filhote": DRAGAO_FILHOTE, "adulto": DRAGAO_ADULTO,
               "estilo": {"pele": PELE_CORUJA, "frente": _coruja_frente}, "ovo": _CORES_OVO_CORUJA},
    "porquinho": {"filhote": PORQUINHO_FILHOTE, "adulto": PORQUINHO_ADULTO,
                  "estilo": {"pele": PELE_PORQUINHO, "frente": _porquinho_frente}, "ovo": _CORES_OVO_PORQUINHO},
    "coala": {"filhote": COALA_FILHOTE, "adulto": COALA_ADULTO,
              "estilo": {"pele": PELE_COALA, "frente": _coala_frente}, "ovo": _CORES_OVO_COALA},
}


# --- animações ---------------------------------------------------------------

def _animacoes_criatura(forma, acessorios, estilo):
    def c(**kw):
        return criatura(forma=forma, acessorios=acessorios, **estilo, **kw)

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
        # Trovoada: escondido e tremendo de medo
        "tremendo": (70, [esc(dx=-1, olhos="arregalado"), esc(dx=1, olhos="arregalado")]),
        # "Aaa..." com a cabeça pra cima e depois o "tchim!" pra baixo
        "espirrando": (300, [c(olhos="fechado", boca="fechada"), c(olhos="fechado", dy=1, boca="aberta")]),
        # Claude Code trabalhando: bracinhos alternando no teclado
        "digitando": (160, [c(olhos="concentrado", braco_esq="baixo", laptop=True),
                            c(olhos="concentrado", braco_dir="baixo", laptop=True)]),
        # Teste falhou: de costas no chão, perninhas tremendo
        "caido": (220, [de_cabeca_pra_baixo(c(olhos="tonto", pernas="balancoA"), forma.topo),
                        de_cabeca_pra_baixo(c(olhos="tonto", pernas="balancoB"), forma.topo)]),
        # Erro no terminal
        "mao_na_cabeca": (300, [c(olhos="apertado", braco_esq="rosto", boca="fechada"),
                                c(olhos="apertado", braco_esq="rosto", boca="aberta")]),
        # Perto da meta semanal de tokens
        "empanturrado": (400, [c(olhos="sonolento", bochecha=True, boca="fechada")] * 6
                         + [c(olhos="fechado", bochecha=True, respira=True)] * 2),
        # Hora de dormir: bocejão
        "bocejando": (450, [c(olhos="sonolento"), c(olhos="fechado", boca="aberta"),
                            c(olhos="fechado", boca="aberta"), c(olhos="sonolento", boca="fechada")]),
        # Música tocando: balança pros lados com um bracinho pra cima de cada vez
        "dancando": (230, [c(olhos="feliz", dx=-1, braco_esq="cima", pernas="passoA"), c(olhos="feliz"),
                           c(olhos="feliz", dx=1, braco_dir="cima", pernas="passoB"), c(olhos="feliz")]),
        # Fiscal do git: "commit?"
        "placa": (500, [c(braco_esq="cima", braco_dir="cima", placa=True),
                        c(braco_esq="cima", braco_dir="cima", placa=True, olhar=1)]),
    }


def _animacoes_ovo(cores=None):
    def ovo(**kw):
        return _desenhar_ovo(cores=cores, **kw)

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


ACESSORIOS_DA_FASE = {"anciao": frozenset({"cartola", "oculos", "barba"})}


def vestir(fase, roupas_do_clima):
    """Junta os acessórios da fase com as outras roupas (clima, datas, loja, fone), sem conflito:
    só um chapéu e um par de óculos (ver CHAPEUS e OCULOS), cachecol esconde a gravata."""
    r = set(ACESSORIOS_DA_FASE.get(fase, ())) | set(roupas_do_clima)
    for lista in (CHAPEUS, OCULOS):
        usados = [nome for nome in lista if nome in r]
        # Fica só o primeiro; o pijama continua (ele também é a roupa do corpo, só perde a touca)
        r -= {nome for nome in usados[1:] if nome != "pijama"}
    if "cachecol" in r:
        r.discard("gravata")
    return frozenset(r)


def _forma(especie, fase):
    bicho = BICHOS[especie]
    return bicho["filhote"] if fase == "filhote" else bicho["adulto"]


@lru_cache(maxsize=None)
def animacoes(fase, roupas=frozenset(), especie="clawd"):
    """nome -> (milissegundos por quadro, lista de quadros) do bicho na fase pedida, com as roupas do clima."""
    bicho = BICHOS[especie]
    if fase == "ovo":
        return _animacoes_ovo(bicho["ovo"])     # ovo não se veste
    return _animacoes_criatura(_forma(especie, fase), vestir(fase, roupas), bicho["estilo"])


def medidas(fase, especie="clawd"):
    """(altura do corpo, meia largura com os braços), em pixels da grade."""
    if fase == "ovo":
        return len(_OVO), len(_OVO[0]) // 2
    f = _forma(especie, fase)
    return ALTURA - f.topo, (LARGURA - 2 * f.x0) // 2 + 2


ANIMACOES = animacoes("clawd")

# Efeitos que flutuam em volta dele
_CORES_EFEITO = {"R": "#E8455A", "W": BRANCO, "Y": "#FFD34D", "Z": "#8FB4FF", "M": "#E8B26A",
                 "K": "#2A2A2A", "G": "#C9D6E3", "B": "#BFE6FF", "A": "#7CC4F2", "D": "#5A606A",
                 "F": "#F28C28", "H": "#E8D28A", "E": "#6BBF59", "P": "#C77DFF", "T": "#4FC3F7"}
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
    # Faísca do espirro do dragão
    "fogo": de_texto([".Y.",
                      "YFY",
                      ".F."], _CORES_EFEITO),
    "floco": de_texto(["W.W",
                       ".W.",
                       "W.W"], _CORES_EFEITO),
    "folha": de_texto(["..E",
                       ".EE",
                       "E.."], _CORES_EFEITO),
    "feno": de_texto(["..H",
                      ".H.",
                      "H.."], _CORES_EFEITO),
    "pena": de_texto([".M",
                      "MW",
                      "M."], _CORES_EFEITO),
    # Notinha musical (música tocando) em duas cores
    "nota": de_texto(["..PP",
                      "..P.",
                      "..P.",
                      "PPP.",
                      "PP.."], _CORES_EFEITO),
    "nota_b": de_texto(["..TT",
                        "..T.",
                        "..T.",
                        "TTT.",
                        "TT.."], _CORES_EFEITO),
    # Confete (aniversário, Ano Novo, Carnaval)
    "confete_r": de_texto(["RR", "RR"], _CORES_EFEITO),
    "confete_y": de_texto(["YY", "YY"], _CORES_EFEITO),
    "confete_a": de_texto(["AA", "AA"], _CORES_EFEITO),
    "confete_e": de_texto(["EE", "EE"], _CORES_EFEITO),
    # Fumacinha da troca de pet
    "fumaca": de_texto([".GGG.",
                        "GGWGG",
                        "GGGGG",
                        ".GGG."], _CORES_EFEITO),
    # Ventiladorzinho (calor): pás em X e em +, alternando pra parecer que gira
    "ventilador_a": de_texto(["B...B",
                              ".B.B.",
                              "..D..",
                              ".B.B.",
                              "B...B",
                              "..D..",
                              "..D..",
                              ".DDD."], _CORES_EFEITO),
    "ventilador_b": de_texto(["..B..",
                              "..B..",
                              "BBDBB",
                              "..B..",
                              "..B..",
                              "..D..",
                              "..D..",
                              ".DDD."], _CORES_EFEITO),
}

# Ícones do menu (coloridos, ao contrário dos emojis que o Tk desenha em preto e branco)
_CORES_ICONE = {"K": PRETO, "W": BRANCO, "O": LARANJA, "S": SOMBRA, "Y": "#FFD34D", "R": "#E8455A",
                "G": "#7BC67B", "B": "#8FB4FF", "M": "#9C6B43", "C": "#D8DEE6", "D": "#5A606A",
                "E": CASCA, "V": VERDE, "Q": VERDE_SOMBRA, "H": CHIFRE, "N": BARRIGA,
                "T": AZUL_TUBARAO, "U": AZUL_TUBARAO_SOMBRA, "X": BARRIGA_TUBARAO,
                "P": PINGUIM, "A": BICO_PATO, "F": FENIX, "L": CHAMA, "Z": CORUJA, "J": DISCO,
                "I": PORQUINHO, "#": PELO_ESCURO, "%": NARIZ_ROSA,
                "q": COALA, "w": COALA_CLARO, "n": NARIZ_COALA}
ICONES = {
    "comida": de_texto(["....MMM.",
                        "...MMMMM",
                        "..MMMMMM",
                        "..MMMMMM",
                        "...MMMM.",
                        "..WW....",
                        ".WW.....",
                        "WW......"], _CORES_ICONE),
    "bola": de_texto(["..KKKK..",
                      ".KWWWWK.",
                      "KWWKKWWK",
                      "KWKKKKWK",
                      "KWWKKWWK",
                      "KWWWWWWK",
                      ".KWWWWK.",
                      "..KKKK.."], _CORES_ICONE),
    "lua": de_texto(["...YYY..",
                     "..YY....",
                     ".YY.....",
                     ".YY.....",
                     ".YY.....",
                     ".YY...Y.",
                     "..YY.YY.",
                     "...YYY.."], _CORES_ICONE),
    "sol": de_texto(["Y..Y..Y",
                     ".Y.Y.Y.",
                     "..YYY..",
                     "YYYYYYY",
                     "..YYY..",
                     ".Y.Y.Y.",
                     "Y..Y..Y"], _CORES_ICONE),
    "pilula": de_texto(["....RRR.",
                        "...RRRRR",
                        "..RRRRRR",
                        ".WWRRRR.",
                        "WWWWRR..",
                        "WWWWW...",
                        "WWWW....",
                        ".WW....."], _CORES_ICONE),
    "grafico": de_texto(["......G.",
                         "......G.",
                         "...Y..G.",
                         "...Y..G.",
                         "R..Y..G.",
                         "R..Y..G.",
                         "CCCCCCCC"], _CORES_ICONE),
    "nuvem": de_texto(["...CC...",
                       "..CCCC..",
                       ".CCCCCC.",
                       "CCCCCCCC",
                       "CCCCCCCC",
                       ".CCCCCC."], _CORES_ICONE),
    "monitor": de_texto(["DDDDDDDD",
                         "DBBBBBBD",
                         "DBBBBBBD",
                         "DBBBBBBD",
                         "DDDDDDDD",
                         "...DD...",
                         "..DDDD.."], _CORES_ICONE),
    "clawd": de_texto([".OOOOOOOO.",
                       ".OOKOOKOO.",
                       "OOOKOOKOOO",
                       ".OOOOOOOO.",
                       ".SSSSSSSS.",
                       ".O.O..O.O."], _CORES_ICONE),
    "janela": de_texto(["DDDDDDDD",
                        "DBBBBBRD",
                        "DDDDDDDD",
                        "DWWWWWWD",
                        "DWWWWWWD",
                        "DWWWWWWD",
                        "DDDDDDDD"], _CORES_ICONE),
    "dragao": de_texto([".H......H.",
                        ".VVVVVVVV.",
                        ".VVKVVKVV.",
                        "VVVKVVKVVV",
                        ".VVNNNNVV.",
                        ".QQQQQQQQ.",
                        "..VV..VV.."], _CORES_ICONE),
    "tubarao": de_texto(["....U.....",
                         "...UU.....",
                         ".TTTTTTTT.",
                         ".TTKTTKTT.",
                         "TTTTTTTTTT",
                         ".TKWKWKWT.",
                         ".TXXXXXXT.",
                         "..TT..TT.."], _CORES_ICONE),
    "pinguim": de_texto(["..PPPPPP..",
                         ".PWWWWWWP.",
                         ".PWKWWKWP.",
                         "PPWWAAWWPP",
                         ".PWWWWWWP.",
                         "..WWWWWW..",
                         "..AA..AA.."], _CORES_ICONE),
    "pato": de_texto([".....Y....",
                      "..YYYYYY..",
                      ".YYKYYKYY.",
                      "YYYAAAAYYY",
                      ".YYYYYYYYY",
                      "..YYYYYY..",
                      "..AA..AA.."], _CORES_ICONE),
    "fenix": de_texto(["...YLLY...",
                       ".FFFFFFFF.",
                       ".FFKFFKFF.",
                       "LFFFYYFFFL",
                       ".FFYYYYFF.",
                       "..FFFFFF..",
                       "..YY..YY.."], _CORES_ICONE),
    "coruja": de_texto([".Z......Z.",
                        ".ZZZZZZZZ.",
                        ".JJJZZJJJ.",
                        "ZJKJZZJKJZ",
                        ".JJJAAJJJ.",
                        "..ZZZZZZ..",
                        "..YY..YY.."], _CORES_ICONE),
    "porquinho": de_texto([".%I....I%.",
                           ".##IWWIII.",
                           ".##KWWKII.",
                           "IIIIW%WIII",
                           ".IIWWWWII.",
                           "..IIIIII..",
                           "..%%..%%.."], _CORES_ICONE),
    "coala": de_texto(["qqq....qqq",
                       "qwqqqqqqwq",
                       ".qqKqqKqq.",
                       ".qqqnnqqq.",
                       ".qqqnnqqq.",
                       "..qwwwwq..",
                       "..qq..qq.."], _CORES_ICONE),
    "ovo": de_texto(["..EEEE..",
                     ".EEEEEE.",
                     ".EEOEEE.",
                     "EEEEEOEE",
                     "EEOEEEEE",
                     "EEEEEOEE",
                     ".EEEEEE.",
                     "..EEEE.."], _CORES_ICONE),
    "alvo": de_texto(["..RRRR..",
                      ".RWWWWR.",
                      "RWRRRRWR",
                      "RWRWWRWR",
                      "RWRWWRWR",
                      "RWRRRRWR",
                      ".RWWWWR.",
                      "..RRRR.."], _CORES_ICONE),
    "relogio": de_texto(["RR....RR",            # despertador: sininhos em cima, ponteiros dentro
                         "R.RRRR.R",
                         ".RWWWWR.",
                         "RWWKWWWR",
                         "RWWKWWWR",
                         "RWWKKKWR",
                         ".RWWWWR.",
                         "R.RRRR.R"], _CORES_ICONE),
    "lista": de_texto(["..DDDD..",             # prancheta com linhas (resumo, fiscal)
                       ".WWWWWW.",
                       ".WKKKKW.",
                       ".WWWWWW.",
                       ".WKKKWW.",
                       ".WWWWWW.",
                       ".WKKKKW.",
                       ".WWWWWW."], _CORES_ICONE),
    "sacola": de_texto(["..M..M..",            # sacolinha de compras (loja)
                        ".M....M.",
                        "OOOOOOOO",
                        "OOOOOOOO",
                        "OOOYYOOO",
                        "OOOYYOOO",
                        "OOOOOOOO",
                        ".SSSSSS."], _CORES_ICONE),
    "bolo": de_texto(["...Y....",              # bolo com velinha (aniversário)
                      "...R....",
                      "..WWWW..",
                      ".RWRRWR.",
                      ".MMMMMM.",
                      ".EEEEEE.",
                      ".MMMMMM.",
                      "KKKKKKKK"], _CORES_ICONE),
    "som": de_texto(["...C....",
                     "..CC..B.",
                     "CCCC...B",
                     "CCCC...B",
                     "CCCC...B",
                     "..CC..B.",
                     "...C...."], _CORES_ICONE),
    "plugue": de_texto(["..C..C..",
                        "..C..C..",
                        ".DDDDDD.",
                        ".DDDDDD.",
                        "..DDDD..",
                        "...DD...",
                        "...OO..."], _CORES_ICONE),
    "moeda": de_texto(["..YYYY..",
                       ".YYMMYY.",
                       "YYMYYYYY",
                       "YYMYYYYY",
                       "YYMYYYYY",
                       "YYYMMYYY",
                       ".YYYYYY.",
                       "..YYYY.."], _CORES_ICONE),
    "porta": de_texto([".MMMMMM.",
                       ".MMMMMM.",
                       ".MMMMMM.",
                       ".MMMMYM.",
                       ".MMMMMM.",
                       ".MMMMMM.",
                       "CCCCCCCC"], _CORES_ICONE),
}


def com_contorno(grade, cor, ate_linha=None):
    """Copia a grade pintando de `cor` cada pixel vazio encostado no desenho (contorno).

    ate_linha: só contorna até essa linha (pra não encher de escuro o vão entre as perninhas).
    """
    g = Grade(grade.largura, grade.altura)
    for y, linha in enumerate(grade.px):
        for x, c in enumerate(linha):
            if c:
                g.ponto(x, y, c)
                continue
            if ate_linha is not None and y > ate_linha:
                continue
            vizinhos = ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
            if any(0 <= vx < grade.largura and 0 <= vy < grade.altura and grade.px[vy][vx]
                   for vx, vy in vizinhos):
                g.ponto(x, y, cor)
    return g


# Ícone do programa (atalho da área de trabalho e janelas): 16x16, escala sem borrar pra 32/48/64/128/256
ICONE_APP = com_contorno(de_texto(["................",
                                   "................",
                                   "................",
                                   "...OOOOOOOOOO...",
                                   "...OOOOOOOOOO...",
                                   "...OOKOOOOKOO...",
                                   ".OOOOKOOOOKOOOO.",
                                   ".OOOOOOOOOOOOOO.",
                                   "...OOOOOOOOOO...",
                                   "...SSSSSSSSSS...",
                                   "....O.O..O.O....",
                                   "....O.O..O.O....",
                                   "....O.O..O.O....",
                                   "................",
                                   "................",
                                   "................"], _CORES_ICONE), "#5C2A1A", ate_linha=9)
