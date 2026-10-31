"""Liga as regras de necessidades.py ao mascote: tempo passando, avisos, sono,
gripe, banho e XP. Com o modo Tamagotchi desligado, os status ficam pausados."""

import logging
import math
import random
import time
from datetime import datetime

from . import config, necessidades, tela

log = logging.getLogger(__name__)

# Avisos: (tipo, texto, intervalo mínimo entre repetições em segundos)
AVISOS = (
    ("doente", "🤒 Tô gripado... me dá um remédio?", 600),
    ("fome", "🍖 Tô com fome...", 600),
    ("energia", "💤 Tô cansadinho...", 900),
    ("felicidade", "😢 Tô me sentindo sozinho...", 600),
    ("sujeira", "🪰 Tô sujinho... esfrega o mouse em mim!", 900),
)


class Tamagotchi:
    def __init__(self, mascote):
        self.m = mascote
        self.d = mascote.estado.dados
        self._ultimo = time.time()           # relógio de parede: pega suspensão do PC
        self._prox_checagem = 0.0
        self._prox_aviso = {tipo: time.time() + 20 for tipo, _, _ in AVISOS}
        self._prox_espirro = time.time() + random.uniform(30, 90)
        self._xp_quebrado = 0.0              # XP passivo acumulando até virar 1
        self._ultimo_carinho_xp = 0.0
        self.acordado_em = 0.0               # evita dormir de novo logo depois de acordar
        self._esfregar = None                # (t, x, y) do último movimento em cima dele
        self._esfregado = 0.0
        self._banho_de = 0.0                 # sujeira quando começou a esfregar
        self.horas_offline = self._aplicar_offline()

    # ------------------------------------------------------------------ estado

    @property
    def ligado(self):
        return self.d["modo_tamagotchi"]

    @property
    def ativo(self):
        """Status só mudam com o modo ligado e depois de sair do ovo."""
        return self.ligado and self.m.fase != "ovo"

    def mudar_modo(self, ligado):
        self.d["modo_tamagotchi"] = ligado
        self._ultimo = time.time()            # o tempo desligado não conta
        self.d["horas_com_fome"] = 0.0
        self.m.efeitos.quantidade_moscas(0)
        if ligado:
            self.m.falar("Modo Tamagotchi ligado!\nCuida de mim, tá? 🥺", 3)
        else:
            self.m.falar("Modo Tamagotchi desligado.\nSó vou passear por aqui 😎", 3)
        self.m.salvar()

    # ------------------------------------------------------------------ tempo

    def _aplicar_offline(self):
        """Desconta dos status o tempo desde o último save (PC desligado ou programa fechado)."""
        if not self.ativo or not self.d.get("ultimo_save"):
            return 0.0
        try:
            antes = datetime.fromisoformat(self.d["ultimo_save"]).timestamp()
        except (TypeError, ValueError):
            return 0.0
        horas = min((time.time() - antes) / 3600, 24 * 30)
        if horas <= 1 / 60:
            return 0.0
        necessidades.simular_offline(self.d, horas)
        log.info("Offline por %.2f h; status agora %s", horas, self.d["status"])
        return horas

    def boas_vindas(self):
        """Frase ao abrir, ou None se ficou pouco tempo fora."""
        if self.horas_offline < 1:
            return None
        texto = f"Senti sua falta!\nFiquei {necessidades.formatar_duracao(self.horas_offline)} sem você"
        if self.d["doente"]:
            texto += "\ne peguei uma gripe... 🤒"
        elif self.d["status"]["fome"] < 25:
            texto += "\ne tô morrendo de fome 🍖"
        return texto

    def tick(self):
        """Chamado todo frame; o trabalho de verdade roda 1 vez por segundo."""
        agora = time.time()
        if agora < self._prox_checagem:
            return
        self._prox_checagem = agora + 1
        dt = agora - self._ultimo
        self._ultimo = agora
        if dt <= 0:
            return

        sozinho = tela.segundos_ocioso() > config.SEGUNDOS_SOZINHO
        dormindo = self.m.acao == "dormindo"
        if self.ativo:
            if dt > 120:
                # O PC ficou suspenso com o programa aberto: conta como offline
                eventos = necessidades.simular_offline(self.d, dt / 3600)
            else:
                eventos = necessidades.passar_tempo(self.d, dt / 3600, dormindo, sozinho)
            if "ficou_doente" in eventos:
                self.m.falar("Atchim! Acho que fiquei gripado... 🤒", 3)

        # XP passivo enquanto você está por perto (o ovo choca mais rápido)
        if not sozinho and not dormindo and dt <= 120:
            self._xp_quebrado += dt / (config.SEGUNDOS_POR_XP_OVO if self.m.fase == "ovo"
                                       else config.SEGUNDOS_POR_XP)
            if self._xp_quebrado >= 1:
                inteiro = int(self._xp_quebrado)
                self._xp_quebrado -= inteiro
                self.ganhar_xp(inteiro)
        self.m.verificar_evolucao()

        self._sono(agora)
        self._avisos(agora)
        self._espirros(agora)
        self._moscas()

    # ------------------------------------------------------------------ XP

    def ganhar_xp(self, n):
        self.d["xp"] += n
        self.m.verificar_evolucao()

    def carinho(self):
        """Clique: felicidade e 1 XP (no máximo a cada 3 s, pra não farmar clicando)."""
        if self.ativo:
            self.m.estado.ajustar_status("felicidade", config.GANHO_CARINHO)
        agora = time.time()
        if agora - self._ultimo_carinho_xp >= 3:
            self._ultimo_carinho_xp = agora
            self.ganhar_xp(1)

    # ------------------------------------------------------------------ rotinas

    def _sono(self, agora):
        m = self.m
        if m.acao == "dormindo":
            dormiu = time.perf_counter() - m.anim_inicio
            if self.ativo:
                if m.estado.status["energia"] >= 95 and dormiu >= 30:
                    m.acordar()
            elif dormiu >= 45:
                m.acordar()
        elif (self.ativo and m.estado.status["energia"] < 15 and m.acao in ("parado", "andando")
              and agora - self.acordado_em > 120):
            m.dormir("💤 Não aguento mais...\nvou tirar um cochilo")

    def _avisos(self, agora):
        m = self.m
        if not self.ativo or m.balao.visivel or m.acao in ("pendurado", "caindo", "dormindo"):
            return
        s = m.estado.status
        condicoes = {
            "doente": self.d["doente"],
            "fome": s["fome"] < 25,
            "energia": s["energia"] < 25,
            "felicidade": s["felicidade"] < 25,
            "sujeira": self.d["sujeira"] > 70,
        }
        for tipo, texto, intervalo in AVISOS:
            if condicoes[tipo] and agora >= self._prox_aviso[tipo]:
                self._prox_aviso[tipo] = agora + intervalo
                m.falar(texto, 4)
                return

    def _espirros(self, agora):
        if (self.ativo and self.d["doente"] and self.m.acao in ("parado", "andando")
                and agora >= self._prox_espirro):
            self._prox_espirro = agora + random.uniform(45, 150)
            self.m.espirrar()

    def _moscas(self):
        suj = self.d["sujeira"]
        n = 0
        if self.ativo:
            n = 3 if suj >= 85 else 2 if suj >= 70 else 1 if suj >= 55 else 0
        self.m.efeitos.quantidade_moscas(n)

    def esfregar(self, x, y):
        """Mouse passando em cima dele sem apertar: limpa a sujeira e solta bolhas."""
        agora = time.perf_counter()
        anterior = self._esfregar
        self._esfregar = (agora, x, y)
        if anterior is None or agora - anterior[0] > 1.5:
            self._banho_de = self.d["sujeira"]   # começou um banho novo
            return
        if not self.ativo:
            return
        dist = math.hypot(x - anterior[1], y - anterior[2])
        antes = self.d["sujeira"]
        if antes <= 0 or dist == 0:
            return
        self.d["sujeira"] = max(0.0, antes - dist * config.LIMPEZA_POR_PIXEL / self.m.k)
        self._esfregado += dist
        if self._esfregado >= 30 * self.m.k:
            self._esfregado = 0.0
            self.m.bolha_em(x, y)
        if self.d["sujeira"] == 0 and self._banho_de >= 20:
            self._banho_de = 0.0
            self.m.estado.ajustar_status("felicidade", 5)
            self.ganhar_xp(5)
            self.m.falar("Cheirosinho! ✨", 2)
