"""Datas especiais: roupinha e comemoração no Natal, Ano Novo, Halloween, Páscoa,
Carnaval, Dia do Programador e no seu aniversário.

A parte de cima é pura (qual é a ocasião de um dia); DatasEspeciais veste o pet
e comemora uma vez por dia.
"""

import re
import time
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Ocasiao:
    id: str
    nome: str
    roupa: str            # acessório do dia (pixelart.CHAPEUS), ou None
    fala: str
    confete: bool = False


OCASIOES = {
    "aniversario": Ocasiao("aniversario", "Seu aniversário", "chapeu_festa",
                           "🎂 Feliz aniversário!!\nParabéns pra você! 🎉", confete=True),
    "natal": Ocasiao("natal", "Natal", "gorro_natal", "🎄 Feliz Natal!\nHo ho ho!"),
    "reveillon": Ocasiao("reveillon", "Réveillon", "chapeu_festa", "🥂 Último dia do ano!\nQue venha o próximo!",
                         confete=True),
    "ano_novo": Ocasiao("ano_novo", "Ano Novo", "chapeu_festa", "🎆 Feliz Ano Novo!", confete=True),
    "halloween": Ocasiao("halloween", "Halloween", "chapeu_bruxa", "🎃 Doces ou travessuras?"),
    "pascoa": Ocasiao("pascoa", "Páscoa", "orelhas_coelho", "🐰 Feliz Páscoa!\nCadê o chocolate? 🍫"),
    "carnaval": Ocasiao("carnaval", "Carnaval", "chapeu_festa", "🎉 É Carnaval!", confete=True),
    "programador": Ocasiao("programador", "Dia do Programador", None,
                           "💻 Feliz Dia do Programador!\n(dia 256 do ano)"),
}


def pascoa(ano):
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher, calendário gregoriano)."""
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(h + l - 7 * m + 114, 31)
    return date(ano, mes, dia + 1)


def ler_aniversario(texto):
    """'25/12' ou '5-3' -> (dia, mês); None se vazio ou inválido."""
    m = re.fullmatch(r"\s*(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*", texto or "")
    if not m:
        return None
    dia, mes = int(m.group(1)), int(m.group(2))
    try:
        date(2000, mes, dia)            # 2000 é bissexto: 29/02 vale
    except ValueError:
        return None
    return dia, mes


def _eh_aniversario(hoje, aniversario):
    if not aniversario:
        return False
    dia, mes = aniversario
    if (dia, mes) == (29, 2) and not _bissexto(hoje.year):
        return (hoje.day, hoje.month) == (28, 2)     # quem nasceu em 29/02 comemora no 28
    return (hoje.day, hoje.month) == (dia, mes)


def _bissexto(ano):
    return ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0)


def ocasiao(hoje, aniversario=None):
    """A ocasião especial do dia (o seu aniversário vem primeiro), ou None."""
    if _eh_aniversario(hoje, aniversario):
        return OCASIOES["aniversario"]
    dia_mes = (hoje.day, hoje.month)
    if dia_mes in ((24, 12), (25, 12)):
        return OCASIOES["natal"]
    if dia_mes == (31, 12):
        return OCASIOES["reveillon"]
    if dia_mes == (1, 1):
        return OCASIOES["ano_novo"]
    if dia_mes == (31, 10):
        return OCASIOES["halloween"]
    p = pascoa(hoje.year)
    if hoje == p:
        return OCASIOES["pascoa"]
    if hoje in (p - timedelta(days=48), p - timedelta(days=47)):      # segunda e terça de Carnaval
        return OCASIOES["carnaval"]
    if hoje.timetuple().tm_yday == 256:
        return OCASIOES["programador"]
    return None


# ---------------------------------------------------------------------- ligado ao pet

class DatasEspeciais:
    def __init__(self, mascote):
        self.m = mascote
        self.d = mascote.estado.dados["rotina"]
        self.atual = None          # Ocasiao de hoje, ou None
        self._dia = None
        self._prox = 0.0

    def roupas(self):
        return {self.atual.roupa} if self.atual and self.atual.roupa else set()

    def aniversario(self):
        return ler_aniversario(self.d.get("aniversario") or "")

    def definir_aniversario(self, texto):
        """Guarda o aniversário ('' apaga). Devolve False se não entendeu a data."""
        texto = (texto or "").strip()
        if texto and not ler_aniversario(texto):
            return False
        dia_mes = ler_aniversario(texto)
        self.d["aniversario"] = f"{dia_mes[0]:02d}/{dia_mes[1]:02d}" if dia_mes else None
        self.d["data_saudada"] = None
        self._dia = None           # recalcula a ocasião já
        self._prox = 0.0
        return True

    def tick(self):
        agora = time.time()
        if agora < self._prox:
            return
        self._prox = agora + 30
        hoje = date.today()
        if hoje != self._dia:
            self._dia = hoje
            self.atual = ocasiao(hoje, self.aniversario())
            self.m.atualizar_roupas()
        m = self.m
        livre = (not m.balao.visivel and m.acao not in ("pendurado", "caindo", "dormindo")
                 and m.lembretes.ativo is None)
        if self.atual and self.d.get("data_saudada") != hoje.isoformat() and livre:
            self.d["data_saudada"] = hoje.isoformat()
            self.comemorar()

    def comemorar(self):
        m, o = self.m, self.atual
        if o is None:
            return
        if m.acao in ("parado", "andando"):
            m.mudar("comemorando", 3)
        m.falar(o.fala, 5)
        if o.confete:
            m.efeitos.confete(m.larg_janela / 2, m.alt_janela - m.sprites.altura_corpo)
        if o.id == "aniversario":
            m.som_do_pet("parabens")
        m.salvar()
