"""Clima pelo Open-Meteo (grátis, sem chave): busca, tradução dos códigos e roupinhas.

As funções de rede só rodam na thread do Clima (nunca na do Tk). O resto é puro,
pra dar pra testar com um JSON de exemplo.
"""

import json
import logging
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)

URL_GEOCODING = "https://geocoding-api.open-meteo.com/v1/search"
URL_PREVISAO = "https://api.open-meteo.com/v1/forecast"

# Códigos de tempo da OMM (WMO) que o Open-Meteo usa -> (categoria, descrição)
CODIGOS = {
    0: ("limpo", "céu limpo"),
    1: ("limpo", "poucas nuvens"),
    2: ("nublado", "parcialmente nublado"),
    3: ("nublado", "nublado"),
    45: ("neblina", "neblina"),
    48: ("neblina", "neblina com geada"),
    51: ("garoa", "garoa fraca"),
    53: ("garoa", "garoa"),
    55: ("garoa", "garoa forte"),
    56: ("garoa", "garoa congelante"),
    57: ("garoa", "garoa congelante forte"),
    61: ("chuva", "chuva fraca"),
    63: ("chuva", "chuva"),
    65: ("chuva", "chuva forte"),
    66: ("chuva", "chuva congelante"),
    67: ("chuva", "chuva congelante forte"),
    71: ("neve", "neve fraca"),
    73: ("neve", "neve"),
    75: ("neve", "neve forte"),
    77: ("neve", "grãos de neve"),
    80: ("chuva", "pancadas de chuva"),
    81: ("chuva", "pancadas de chuva fortes"),
    82: ("chuva", "temporal de chuva"),
    85: ("neve", "pancadas de neve"),
    86: ("neve", "pancadas de neve fortes"),
    95: ("tempestade", "trovoada"),
    96: ("tempestade", "trovoada com granizo"),
    99: ("tempestade", "trovoada com granizo forte"),
}

EMOJI = {"limpo": "☀", "nublado": "☁", "neblina": "🌫", "garoa": "🌦", "chuva": "🌧",
         "neve": "❄", "tempestade": "⛈"}

FRIO = 15          # abaixo disso: cachecol
CALOR = 30         # acima disso: ventiladorzinho
CHANCE_CHUVA = 50  # % por hora a partir da qual ele avisa que vai chover


@dataclass
class Clima:
    temperatura: float
    sensacao: float
    codigo: int
    eh_dia: bool
    vento: float
    hora_local: datetime                       # hora da cidade (sem fuso) no momento da leitura
    chuva_por_hora: list = field(default_factory=list)   # [(datetime local, % de chance)]

    @property
    def categoria(self):
        return CODIGOS.get(self.codigo, ("nublado", "tempo indefinido"))[0]

    @property
    def descricao(self):
        return CODIGOS.get(self.codigo, ("nublado", "tempo indefinido"))[1]

    @property
    def emoji(self):
        if self.categoria == "limpo" and not self.eh_dia:
            return "🌙"
        return EMOJI[self.categoria]

    @property
    def chovendo(self):
        return self.categoria in ("garoa", "chuva", "tempestade")

    def para_save(self):
        return {"temperatura": self.temperatura, "sensacao": self.sensacao, "codigo": self.codigo,
                "eh_dia": self.eh_dia, "vento": self.vento, "hora_local": self.hora_local.isoformat(),
                "chuva_por_hora": [[h.isoformat(), p] for h, p in self.chuva_por_hora]}

    @classmethod
    def do_save(cls, d):
        return cls(d["temperatura"], d["sensacao"], d["codigo"], d["eh_dia"], d["vento"],
                   datetime.fromisoformat(d["hora_local"]),
                   [(datetime.fromisoformat(h), p) for h, p in d.get("chuva_por_hora", [])])


# ---------------------------------------------------------------------- rede

def _baixar_json(url, params, timeout=15):
    pedido = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}",
                                    headers={"User-Agent": "clawd-desktop-pet"})
    with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
        return json.load(resposta)


def procurar_cidade(nome, estado=None, pais="BR", baixar=_baixar_json):
    """(nome, estado, lat, lon) da cidade, preferindo o estado pedido; None se não achar."""
    dados = baixar(URL_GEOCODING, {"name": nome, "count": 10, "language": "pt", "format": "json",
                                   "countryCode": pais})
    resultados = dados.get("results") or []
    if estado:
        alvo = estado.strip().lower()
        no_estado = [r for r in resultados if (r.get("admin1") or "").lower() == alvo]
        resultados = no_estado or resultados
    if not resultados:
        return None
    # Com nomes repetidos, a mais populosa costuma ser a certa
    r = max(resultados, key=lambda r: r.get("population") or 0)
    return r["name"], r.get("admin1") or "", r["latitude"], r["longitude"]


def buscar_previsao(lat, lon, baixar=_baixar_json):
    dados = baixar(URL_PREVISAO, {
        "latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 1,
        "current": "temperature_2m,apparent_temperature,weather_code,is_day,wind_speed_10m",
        "hourly": "precipitation_probability"})
    return ler_previsao(dados)


def ler_previsao(dados):
    """JSON do Open-Meteo -> Clima."""
    atual = dados["current"]
    horas = dados.get("hourly") or {}
    chuva = [(datetime.fromisoformat(h), p) for h, p in
             zip(horas.get("time", []), horas.get("precipitation_probability", [])) if p is not None]
    return Clima(temperatura=float(atual["temperature_2m"]),
                 sensacao=float(atual.get("apparent_temperature", atual["temperature_2m"])),
                 codigo=int(atual["weather_code"]), eh_dia=bool(atual.get("is_day", 1)),
                 vento=float(atual.get("wind_speed_10m") or 0),
                 hora_local=datetime.fromisoformat(atual["time"]), chuva_por_hora=chuva)


def agora_na_cidade(dados_ou_offset):
    """Hora local da cidade, a partir do utc_offset_seconds do Open-Meteo."""
    offset = dados_ou_offset if isinstance(dados_ou_offset, int) else dados_ou_offset.get("utc_offset_seconds", 0)
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=offset)


# ---------------------------------------------------------------------- regras

def roupas(c):
    """Acessórios que o tempo pede. Conjunto de nomes que o pixelart sabe desenhar."""
    if c is None:
        return frozenset()
    r = set()
    if c.categoria == "limpo" and c.eh_dia:
        r.add("oculos_sol")
    if c.categoria in ("garoa", "chuva"):
        r |= {"guarda_chuva", "galochas"}
    if c.categoria == "neve":
        r |= {"gorro", "cachecol"}
    if c.temperatura < FRIO:
        r.add("cachecol")
    if not c.eh_dia:
        r.add("pijama")
    return frozenset(r)


def efeitos_nos_status(c):
    """Como o tempo mexe nas necessidades: multiplicadores e bônus por hora."""
    efeito = {"mult_fome": 1.0, "mult_energia": 1.0, "bonus_felicidade": 0.0, "dorminhoco": False}
    if c is None:
        return efeito
    if c.categoria == "limpo" and c.eh_dia:
        efeito["bonus_felicidade"] = 4.0          # sol: a felicidade sobe em vez de cair
    if c.chovendo:
        efeito["mult_energia"] = 1.3              # chuva: preguiça
        efeito["dorminhoco"] = True               # ...e cochila mais
    if c.temperatura < FRIO:
        efeito["mult_fome"] = 1.5                 # frio: fome cai mais rápido
    return efeito


def proxima_chuva(c, a_partir_de, ate_hora=23, minimo=CHANCE_CHUVA):
    """(hora, chance) da primeira hora de hoje com chance >= mínimo depois de a_partir_de, ou None."""
    if c is None:
        return None
    for hora, chance in c.chuva_por_hora:
        if hora > a_partir_de and hora.date() == a_partir_de.date() and hora.hour <= ate_hora \
                and chance >= minimo:
            return hora, chance
    return None


def resumo(c, cidade, agora=None):
    """Texto do balão do menu Clima. A chance de chuva olha só as próximas horas de hoje."""
    linhas = [f"{c.emoji} {cidade}: {round(c.temperatura)}°C, {c.descricao}",
              f"Sensação de {round(c.sensacao)}°C · vento {round(c.vento)} km/h"]
    agora = agora or c.hora_local
    futuras = [(h, p) for h, p in c.chuva_por_hora
               if h >= agora.replace(minute=0, second=0, microsecond=0) and h.date() == agora.date()]
    maior = max(futuras, key=lambda hp: hp[1], default=None)
    if maior and maior[1] >= 20:
        linhas.append(f"Chuva mais tarde: até {maior[1]}% lá pelas {maior[0].hour}h")
    return "\n".join(linhas)
