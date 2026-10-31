"""Regras do tamagotchi sem Tk: como os status mudam com o tempo, doença e evolução.

Os status vão de 0 a 100 e 100 é ótimo (fome 100 = barriga cheia).
A sujeira é o contrário: 0 = limpinho.
"""

from dataclasses import dataclass

# Fases de evolução e o XP mínimo de cada uma
FASES = (("ovo", 0), ("filhote", 100), ("clawd", 1000), ("anciao", 10000))
NOMES_FASE = {"ovo": "Ovo", "filhote": "Filhote", "clawd": "Clawd", "anciao": "Clawd ancião"}
ORDEM_FASE = {nome: i for i, (nome, _) in enumerate(FASES)}


def fase_por_xp(xp):
    atual = FASES[0][0]
    for nome, minimo in FASES:
        if xp >= minimo:
            atual = nome
    return atual


def proxima_fase(xp):
    """(nome, xp necessário) da próxima fase, ou None se já está na última."""
    for nome, minimo in FASES:
        if xp < minimo:
            return nome, minimo
    return None


def xp_minimo(fase):
    return dict(FASES)[fase]


@dataclass(frozen=True)
class Taxas:
    """Quanto cada coisa muda por hora."""
    fome_acordado: float = 6
    fome_dormindo: float = 3
    fome_offline: float = 2          # com o PC desligado ele hiberna e gasta menos
    energia_acordado: float = 7
    energia_dormindo: float = 40     # recupera dormindo
    energia_doente: float = 6        # gasto extra quando está gripado
    felicidade_presente: float = 2
    felicidade_sozinho: float = 6    # você está longe do PC
    felicidade_offline: float = 2
    felicidade_doente: float = 2
    sujeira_acordado: float = 5
    sujeira_dormindo: float = 2
    sujeira_offline: float = 1
    limiar_fome_doenca: float = 20   # fome abaixo disso por...
    horas_para_doenca: float = 2     # ...esse tempo deixa ele gripado


TAXAS = Taxas()


def _limitar(valor):
    return max(0.0, min(100.0, valor))


def passar_tempo(d, horas, dormindo=False, sozinho=False, offline=False, taxas=TAXAS, mult_energia=1.0):
    """Aplica `horas` de vida aos dados do save (dict do clawd.json).

    mult_energia multiplica o gasto de energia acordado (empanturrado de tokens = 1.5).

    Devolve a lista de eventos que aconteceram, por enquanto só "ficou_doente".
    """
    s = d["status"]
    if offline:
        dormindo = True
        fome, felicidade, sujeira = taxas.fome_offline, taxas.felicidade_offline, taxas.sujeira_offline
    else:
        fome = taxas.fome_dormindo if dormindo else taxas.fome_acordado
        felicidade = taxas.felicidade_sozinho if sozinho else taxas.felicidade_presente
        sujeira = taxas.sujeira_dormindo if dormindo else taxas.sujeira_acordado
    energia = taxas.energia_dormindo if dormindo else -taxas.energia_acordado * mult_energia
    if d["doente"]:
        energia -= taxas.energia_doente
        felicidade += taxas.felicidade_doente

    s["fome"] = _limitar(s["fome"] - fome * horas)
    s["energia"] = _limitar(s["energia"] + energia * horas)
    s["felicidade"] = _limitar(s["felicidade"] - felicidade * horas)
    d["sujeira"] = _limitar(d["sujeira"] + sujeira * horas)

    # Doença: ficar muito tempo com fome deixa ele gripado
    eventos = []
    if s["fome"] < taxas.limiar_fome_doenca:
        d["horas_com_fome"] += horas
    else:
        d["horas_com_fome"] = 0.0
    if not d["doente"] and d["horas_com_fome"] >= taxas.horas_para_doenca:
        d["doente"] = True
        eventos.append("ficou_doente")
    return eventos


def simular_offline(d, horas, passo=1 / 60, taxas=TAXAS):
    """Tempo com o programa fechado, em passos de 1 minuto pra doença contar certo."""
    eventos = []
    restante = horas
    while restante > 0:
        h = min(passo, restante)
        eventos += passar_tempo(d, h, offline=True, taxas=taxas)
        restante -= h
    return eventos


def formatar_duracao(horas):
    """1.5 -> '1h30', 0.25 -> '15 min', 50 -> '2 dias'."""
    if horas >= 48:
        return f"{int(horas // 24)} dias"
    if horas >= 1:
        h, m = int(horas), int(round((horas % 1) * 60))
        if m == 60:
            h, m = h + 1, 0
        return f"{h}h{m:02d}" if m else f"{h}h"
    return f"{max(1, int(round(horas * 60)))} min"
