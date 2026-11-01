"""Resumo do dia: tempo no PC, tasks e tokens do Claude Code, testes, projetos e
quanto você cuidou do pet. Aparece sozinho às 18h e pelo menu a qualquer hora.
"""

import time
from datetime import date, datetime

from . import tela, tokens

HORA_DO_RESUMO = 18
SEGUNDOS_PRA_CONTAR_PC = 300     # mexeu no PC nesse tempo = você está no PC
CONTADORES = ("minutos_pc", "carinhos", "comidas", "brincadeiras")


def _horas(minutos):
    h, m = divmod(int(minutos), 60)
    return f"{h}h{m:02d}" if h else f"{m} min"


def texto(pet, claude, formatar_tokens=tokens.formatar):
    """Monta o balão. pet: contadores do dia; claude: o dia no histórico do Claude Code (ou {})."""
    linhas = ["📋 Resumo de hoje"]
    if pet.get("minutos_pc"):
        linhas.append(f"⏱ {_horas(pet['minutos_pc'])} no PC")
    tasks = claude.get("tasks", 0)
    if tasks:
        linhas.append(f"🤖 {tasks} task{'s' if tasks > 1 else ''} · {formatar_tokens(claude.get('tokens', 0))} tokens")
    testes = []
    if claude.get("testes_ok"):
        testes.append(f"✅ {claude['testes_ok']} testes ok")
    if claude.get("testes_falha"):
        testes.append(f"❌ {claude['testes_falha']} falharam")
    if testes:
        linhas.append(" · ".join(testes))
    projetos = [p for p in claude.get("projetos", []) if p]
    if projetos:
        extra = f" +{len(projetos) - 3}" if len(projetos) > 3 else ""
        linhas.append("📁 " + ", ".join(projetos[:3]) + extra)
    cuidados = [f"{emoji} {pet[chave]} {nome}{'s' if pet[chave] > 1 else ''}" for chave, emoji, nome in
                (("carinhos", "♥", "carinho"), ("comidas", "🍤", "comida"), ("brincadeiras", "🎾", "brincadeira"))
                if pet.get(chave)]
    if cuidados:
        linhas.append(" · ".join(cuidados))
    if len(linhas) == 1:
        linhas.append("Dia tranquilo hoje 😌")
    elif tasks >= 10:
        linhas.append("Dia produtivo! 💪")
    elif pet.get("minutos_pc", 0) >= 8 * 60:
        linhas.append("Bastante tela hoje... descansa! 👀")
    return "\n".join(linhas)


class ResumoDoDia:
    def __init__(self, mascote):
        self.m = mascote
        self.rotina = mascote.estado.dados["rotina"]
        self._prox_minuto = time.time() + 60
        self._prox_auto = 0.0

    def hoje(self):
        """Contadores de hoje (zera quando vira o dia)."""
        dados = self.m.estado.dados
        d = dados.get("hoje")
        if not isinstance(d, dict) or d.get("data") != date.today().isoformat():
            d = dados["hoje"] = {"data": date.today().isoformat(), **{c: 0 for c in CONTADORES}}
        return d

    def contar(self, chave, n=1):
        d = self.hoje()
        d[chave] = d.get(chave, 0) + n

    def texto(self):
        cc = self.m.cc
        claude = cc.d["historico"].get(date.today().isoformat(), {})
        return texto(self.hoje(), claude)

    def mostrar(self):
        self.m.falar(self.texto(), 10)

    @property
    def automatico(self):
        return self.rotina["resumo_auto"]

    def alternar_automatico(self):
        self.rotina["resumo_auto"] = not self.rotina["resumo_auto"]

    def tick(self):
        agora = time.time()
        if agora >= self._prox_minuto:
            self._prox_minuto = agora + 60
            if tela.segundos_ocioso() < SEGUNDOS_PRA_CONTAR_PC:
                self.contar("minutos_pc")
        if agora < self._prox_auto:
            return
        self._prox_auto = agora + 30
        m = self.m
        hoje = date.today().isoformat()
        if (self.automatico and datetime.now().hour >= HORA_DO_RESUMO and self.rotina.get("resumo_mostrado") != hoje
                and not m.balao.visivel and m.lembretes.ativo is None and tela.segundos_ocioso() < 60
                and m.acao not in ("pendurado", "caindo", "dormindo")):
            self.rotina["resumo_mostrado"] = hoje
            self.mostrar()
