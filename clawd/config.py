"""Constantes do mascote. Valores de movimento estão em pixels por segundo na
escala 4 (DPI 96) e são multiplicados pelo fator da tela em tempo de execução."""

from pathlib import Path

# Caminhos
PASTA_BASE = Path(__file__).resolve().parent.parent
ARQUIVO_ESTADO = PASTA_BASE / "clawd.json"
ARQUIVO_LOG = PASTA_BASE / "clawd.log"
PASTA_SPRITES = PASTA_BASE / "sprites"

# Janela
COR_CHAVE = "#010101"   # cor que o Windows deixa transparente (quase preto, pra bordas ficarem escuras)
TICK_MS = 33            # intervalo do loop de animação (~30 fps)
MARGEM_LATERAL = 4      # espaço extra dos lados, em pixels da grade (pras estrelinhas)
MARGEM_TOPO = 12        # espaço extra em cima, em pixels da grade (pro coração e Zzz)

# Andar
VELOCIDADE_ANDAR = 40

# Física
GRAVIDADE = 2600
QUIQUE_PAREDE = 0.55    # quanto da velocidade sobra ao bater na parede
QUIQUE_CHAO = 0.4       # quanto da velocidade sobra ao quicar no chão
ATRITO_CHAO = 2200      # desaceleração quando escorrega no chão
VEL_MIN_QUIQUE = 260    # abaixo disso ele para de quicar e assenta
VEL_MAX = 4500          # teto pra arremessos muito fortes
VEL_PULO = 520          # pulinho de comemoração

# Interação
LIMIAR_CLIQUE = 5            # menos que isso entre apertar e soltar é clique (pixels reais)
LIMIAR_ARREMESSO = 700       # velocidade mínima do mouse pra contar como arremesso
VEL_AI = 1500                # batida na parede acima disso faz ele reclamar
SACUDIDA_REVERSOES = 6       # trocas de direção que deixam ele tonto
SACUDIDA_JANELA = 1.6        # ...dentro desse intervalo (segundos)
SACUDIDA_AMPLITUDE = 30      # tamanho mínimo de cada chacoalhada
TONTO_SEGUNDOS = 4.0
PERDA_TONTURA = 8            # felicidade perdida ao ficar tonto
GANHO_CARINHO = 2            # felicidade ganha por clique

# Tamagotchi (as taxas por hora ficam em necessidades.Taxas)
SEGUNDOS_SOZINHO = 300       # sem mexer no PC por esse tempo = você saiu, ele fica sozinho
SEGUNDOS_POR_XP = 60         # XP passivo: 1 por minuto com você por perto
SEGUNDOS_POR_XP_OVO = 10     # o ovo choca mais rápido (~17 min até 100 XP)
LIMPEZA_POR_PIXEL = 0.04     # sujeira tirada por pixel de mouse esfregado
XP_ALIMENTAR = 5
XP_BRINCAR = 5
XP_REMEDIO = 2

# Rotina
TOPMOST_MS = 3000       # de quanto em quanto tempo reforça "sempre por cima"
AREA_MS = 5000          # de quanto em quanto tempo relê a área de trabalho
AUTOSAVE_MS = 60000


def escala_para_dpi(dpi):
    """Tamanho de cada pixel da arte: 4 em 96 DPI, 5 em 120 DPI (125%) etc."""
    return max(2, round(4 * dpi / 96))
