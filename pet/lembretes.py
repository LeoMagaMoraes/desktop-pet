"""Lembretes: você escreve o que e quando, e o pet te lembra na hora.

A parte de cima é pura (entende "amanhã 9h", "daqui a 20 min"...) e dá pra
testar. Lembretes é o controle ligado ao pet: dispara na hora, acena até você
clicar nele, adia e reagenda os diários.
"""

import re
import time
import uuid
from datetime import datetime, timedelta

DIAS_SEMANA = {"segunda": 0, "terça": 1, "terca": 1, "quarta": 2, "quinta": 3, "sexta": 4,
               "sábado": 5, "sabado": 5, "domingo": 6}
NOMES_DIA = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")
HORA_PADRAO = 9          # "amanhã" sem hora vira amanhã às 9h

_UNIDADES = {"m": 1, "min": 1, "mins": 1, "minuto": 1, "minutos": 1,
             "h": 60, "hr": 60, "hrs": 60, "hora": 60, "horas": 60,
             "d": 1440, "dia": 1440, "dias": 1440}


def _minutos_relativos(t):
    """'daqui a 20 min', 'em 2 horas', 'em 1h30', '1 hora e 15' -> minutos, ou None.

    Sem "daqui a"/"em", "15h" e "1h30" são horário do relógio, não "daqui a 15 horas".
    """
    m = re.fullmatch(r"(daqui\s+a\s+|daqui\s+|em\s+|dentro\s+de\s+)?"
                     r"(\d+)\s*(m|min|mins|minutos?|h|hrs?|horas?|d|dias?)"
                     r"(?:\s*(?:e\s+)?(\d+)\s*(m|min|mins|minutos?)?)?", t)
    if not m or (m.group(3) == "h" and not m.group(1)):
        return None
    total = int(m.group(2)) * _UNIDADES[m.group(3)]
    if m.group(4):
        # "em 1h30" ou "1 hora e 30": o resto são minutos
        if _UNIDADES[m.group(3)] == 1 and not m.group(5):
            return None
        total += int(m.group(4))
    return total


def ler_hora(t):
    """(hora, minuto) escritos no texto, ou None. Aceita 15:30, 15h, 15h30, às 15, meio-dia."""
    if "meio-dia" in t or "meio dia" in t:
        return 12, 0
    if "meia-noite" in t or "meia noite" in t:
        return 0, 0
    m = re.search(r"\b(\d{1,2})\s*(?::|h)\s*(\d{2})?\b", t) or re.search(r"\b(?:às|as)\s+(\d{1,2})\b()", t)
    if not m:
        return None
    hora, minuto = int(m.group(1)), int(m.group(2) or 0)
    if hora > 23 or minuto > 59:
        return None
    return hora, minuto


def interpretar(texto, agora=None):
    """Entende quando lembrar. Devolve (datetime, repetir) ou (None, None).

    repetir é "diario" pra "todo dia ..."; senão None.
    """
    agora = agora or datetime.now()
    t = " ".join((texto or "").lower().replace(",", " ").split())
    if not t:
        return None, None

    repetir = None
    if re.search(r"\btodos?\s+(?:o\s+|os\s+)?dias?\b", t):
        repetir = "diario"
        t = re.sub(r"\btodos?\s+(?:o\s+|os\s+)?dias?\b", "", t).strip()

    minutos = None if repetir else _minutos_relativos(t)
    if minutos is not None:
        return (agora + timedelta(minutes=minutos)).replace(second=0, microsecond=0), None

    hora = ler_hora(t)
    dia = None
    data = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", t)
    if data:
        d, mes, ano = int(data.group(1)), int(data.group(2)), data.group(3)
        ano = int(ano) + (2000 if ano and len(ano) == 2 else 0) if ano else agora.year
        try:
            dia = datetime(ano, mes, d).date()
        except ValueError:
            return None, None
        if not data.group(3) and dia < agora.date():
            dia = dia.replace(year=dia.year + 1)          # 25/12 que já passou: ano que vem
    elif "depois de amanhã" in t or "depois de amanha" in t:
        dia = (agora + timedelta(days=2)).date()
    elif "amanhã" in t or "amanha" in t:
        dia = (agora + timedelta(days=1)).date()
    elif "hoje" in t:
        dia = agora.date()
    else:
        for nome, numero in DIAS_SEMANA.items():
            if re.search(rf"\b{nome}\b", t):
                faltam = (numero - agora.weekday()) % 7
                dia = (agora + timedelta(days=faltam)).date()
                if faltam == 0 and hora and (hora[0], hora[1]) <= (agora.hour, agora.minute):
                    dia += timedelta(days=7)               # "sexta 14h" numa sexta às 15h: a próxima
                break

    if dia is None and hora is None:
        return None, None
    if hora is None:
        hora = (HORA_PADRAO, 0)
    if dia is None:
        dia = agora.date()
        if (hora[0], hora[1]) <= (agora.hour, agora.minute):
            dia += timedelta(days=1)                       # "15:30" que já passou hoje: amanhã
    quando = datetime(dia.year, dia.month, dia.day, hora[0], hora[1])
    if quando <= agora and not repetir:
        return None, None
    return quando, repetir


def formatar(quando, agora=None, repetir=None):
    """'hoje às 15:30', 'amanhã às 09:00', 'sábado (08/11) às 14:00', '25/12/2027 às 08:00'."""
    agora = agora or datetime.now()
    hora = quando.strftime("%H:%M")
    if repetir == "diario":
        return f"todo dia às {hora}"
    dias = (quando.date() - agora.date()).days
    if dias == 0:
        return f"hoje às {hora}"
    if dias == 1:
        return f"amanhã às {hora}"
    if 1 < dias < 7:
        return f"{NOMES_DIA[quando.weekday()]} ({quando:%d/%m}) às {hora}"
    if quando.year == agora.year:
        return f"{quando:%d/%m} às {hora}"
    return f"{quando:%d/%m/%Y} às {hora}"


def novo(texto, quando, repetir=None):
    return {"id": uuid.uuid4().hex[:8], "texto": texto.strip(), "quando": quando.isoformat(timespec="minutes"),
            "repetir": repetir}


def quando_de(lembrete):
    return datetime.fromisoformat(lembrete["quando"])


def valido(lembrete):
    """Descarta lembrete estragado no save (sem texto ou com data ilegível)."""
    try:
        return bool(lembrete.get("id") and lembrete.get("texto")) and quando_de(lembrete) is not None
    except (AttributeError, TypeError, ValueError):
        return False


# ---------------------------------------------------------------------- ligado ao pet

ADIAR_MINUTOS = 10
ATRASO_AVISADO = timedelta(minutes=2)     # disparou com mais atraso que isso: diz o horário original
ESPERA_AO_ABRIR = 3                       # segundos: deixa o "oi" de boas-vindas aparecer primeiro


class Lembretes:
    def __init__(self, mascote):
        self.m = mascote
        dados = mascote.estado.dados
        if not isinstance(dados.get("lembretes"), list):
            dados["lembretes"] = []
        dados["lembretes"][:] = [l for l in dados["lembretes"] if isinstance(l, dict) and valido(l)]
        self.lista = dados["lembretes"]
        self.ativo = None                  # lembrete tocando agora (o pet acenando)
        self._texto_ativo = ""
        self._prox_checagem = time.time() + ESPERA_AO_ABRIR

    def proximos(self):
        return sorted(self.lista, key=quando_de)

    def adicionar(self, texto, quando, repetir=None):
        lembrete = novo(texto, quando, repetir)
        self.lista.append(lembrete)
        self.m.salvar()
        self.m.falar(f"Combinado! ⏰\nTe lembro {formatar(quando, repetir=repetir)}", 3)
        return lembrete

    def apagar(self, ident):
        self.lista[:] = [l for l in self.lista if l["id"] != ident]
        self.m.salvar()

    # ------------------------------------------------------------------ disparo

    def tick(self):
        agora_t = time.time()
        if self.m.demo or agora_t < self._prox_checagem:
            return
        self._prox_checagem = agora_t + 1
        m = self.m
        if self.ativo is None:
            agora = datetime.now()
            vencidos = [l for l in self.lista if quando_de(l) <= agora]
            if vencidos:
                self._disparar(min(vencidos, key=quando_de), agora)
        if self.ativo is not None:
            # Acena até você clicar nele (se ninguém estiver arrastando ou ele estiver no ar)
            if m.acao in ("parado", "andando", "digitando", "dormindo"):
                m.mudar("acenando")
            if not m.balao.visivel or not m.balao.texto.startswith("⏰"):
                m.falar(self._texto_ativo, fixo=True)

    def _disparar(self, lembrete, agora):
        quando = quando_de(lembrete)
        texto = f"⏰ Lembrete:\n{lembrete['texto']}"
        if agora - quando > ATRASO_AVISADO:
            texto += f"\n(era pra {formatar(quando, agora)})"
        if lembrete.get("repetir") == "diario":
            # Diário: já marca o próximo (pulando os dias que o PC ficou desligado)
            proximo = quando
            while proximo <= agora:
                proximo += timedelta(days=1)
            lembrete["quando"] = proximo.isoformat(timespec="minutes")
        else:
            self.lista.remove(lembrete)
        self.ativo = lembrete
        self._texto_ativo = texto
        self.m.cc.parar_espera()
        if self.m.acao == "dormindo":
            # Acorda pra avisar (e não volta a dormir logo em seguida)
            self.m.tama.cochilo_ate = None
            self.m.tama.acordado_em = time.time()
        self.m.mudar("acenando")
        self.m.falar(texto, fixo=True)
        self.m.som_do_pet("lembrete")
        self.m.salvar()

    def dispensar(self, falar=True):
        """Clicou no pet (ou no 'Feito!' do menu): para de acenar."""
        if self.ativo is None:
            return False
        self.ativo = None
        if self.m.balao.texto.startswith("⏰"):
            self.m.balao.esconder()
        if self.m.acao == "acenando":
            self.m.mudar("parado", 1.5)
        if falar:
            self.m.falar("Beleza! ✅", 1.5)
        return True

    def adiar(self, minutos=ADIAR_MINUTOS):
        if self.ativo is None:
            return
        quando = (datetime.now() + timedelta(minutes=minutos)).replace(second=0, microsecond=0)
        self.lista.append(novo(self.ativo["texto"], quando))
        self.dispensar(falar=False)
        self.m.falar(f"Te lembro de novo às {quando:%H:%M} ⏰", 2.5)
        self.m.salvar()
