"""Hora de dormir: passou do horário que você escolheu, ele boceja e te manda ir
dormir. Se você sair do PC, ele dorme também.
"""

import random
import time
from datetime import datetime

from . import lembretes, tela

FIM_DA_NOITE = 5               # até 5h da manhã ainda conta como "depois da hora"
MINUTOS_ENTRE_AVISOS = 20
MINUTOS_OCIOSO_PRA_DORMIR = 10
FRASES = ["🥱 Bora dormir?", "🥱 Amanhã a gente continua...", "😴 Meus olhos tão pesados...\ne os seus?",
          "🛏️ A cama tá te chamando!"]


def ler(texto):
    """'23:00', '23h', 'meia-noite' -> 'HH:MM'; None se vazio ou não entendeu."""
    hora = lembretes.ler_hora(" ".join((texto or "").lower().split()))
    return f"{hora[0]:02d}:{hora[1]:02d}" if hora else None


def passou_da_hora(agora, hora_dormir):
    """True entre a hora de dormir e as 5h da manhã. hora_dormir: 'HH:MM'."""
    h, m = map(int, hora_dormir.split(":"))
    alvo, minutos, fim = h * 60 + m, agora.hour * 60 + agora.minute, FIM_DA_NOITE * 60
    if alvo >= fim:                      # 23:00 -> das 23h até a meia-noite e da meia-noite até 5h
        return minutos >= alvo or minutos < fim
    return alvo <= minutos < fim         # 1:00 -> da 1h até 5h


class HoraDeDormir:
    def __init__(self, mascote):
        self.m = mascote
        self.d = mascote.estado.dados["rotina"]
        self._prox = 0.0
        self._ultimo_aviso = 0.0
        self._avisou_hoje = False        # primeiro aviso da noite já foi?
        self._dormiu_hoje = False

    @property
    def hora(self):
        return self.d.get("hora_dormir")

    def definir(self, texto):
        """'' desliga. Devolve False se não entendeu o horário."""
        texto = (texto or "").strip()
        if not texto:
            self.d["hora_dormir"] = None
            return True
        hora = ler(texto)
        if hora is None:
            return False
        self.d["hora_dormir"] = hora
        self._avisou_hoje = self._dormiu_hoje = False
        self._ultimo_aviso = 0.0
        return True

    def tick(self):
        agora_t = time.time()
        if agora_t < self._prox:
            return
        self._prox = agora_t + 5
        if not self.hora or not passou_da_hora(datetime.now(), self.hora):
            self._avisou_hoje = self._dormiu_hoje = False      # de dia: zera pra próxima noite
            return
        m = self.m
        if m.lembretes.ativo is not None or m.acao in ("pendurado", "caindo"):
            return
        ocioso = tela.segundos_ocioso()
        if ocioso >= MINUTOS_OCIOSO_PRA_DORMIR * 60:
            if m.acao in ("parado", "andando") and not self._dormiu_hoje:
                self._dormiu_hoje = True
                m.dormir("Você foi dormir?\nEu também... 💤")
            return
        if ocioso > 60 or m.balao.visivel or agora_t - self._ultimo_aviso < MINUTOS_ENTRE_AVISOS * 60:
            return
        self._ultimo_aviso = agora_t
        if not self._avisou_hoje:
            self._avisou_hoje = True
            texto = f"🌙 Já passou das {self.hora}!\nHora de ir dormir..."
        else:
            texto = random.choice(FRASES)
        if m.acao in ("parado", "andando"):
            m.mudar("bocejando", 2.7)
        m.falar(texto, 4)
