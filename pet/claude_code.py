"""Integração com o Claude Code: lê os eventos que os hooks gravam e faz o Clawd reagir.

Também conta os tokens da semana numa thread e cuida da meta semanal e dos
dias sem usar o Claude.
"""

import json
import logging
import threading
import time
from datetime import date, datetime, timedelta

from . import config, especies, sons, tela, tokens

log = logging.getLogger(__name__)

DIAS_HISTORICO = 30


def _epoch(iso):
    try:
        return datetime.fromisoformat(iso).timestamp() if iso else 0.0
    except (TypeError, ValueError):
        return 0.0


class ClaudeCode:
    def __init__(self, mascote):
        self.m = mascote
        self.d = mascote.estado.dados["claude"]
        base = tokens.pasta_claude()
        self.arq_eventos = base / "pet-eventos.jsonl"
        self.arq_status = base / "pet-status.json"
        # Começa do fim do log: eventos de antes de abrir o Clawd não contam
        try:
            self.offset = self.arq_eventos.stat().st_size
        except OSError:
            self.offset = 0

        status = self._ler_status()
        self.sessao = status.get("tokens_sessao")        # tokens da sessão mais recente
        self.ultima_task = None                          # tokens da última task finalizada
        self.trabalhando = {}                            # session_id -> hora do último evento
        self.esperando = None                            # hora da notificação "preciso de você"

        self.semana = None                               # tokens dos últimos 7 dias
        self._contador = tokens.ContadorSemana(base / "projects")
        self._thread = None
        self._prox_semana = 0.0
        self._prox_checagem = 0.0
        self._prox_dias = time.time() + 30
        self._ultimo_erro = 0.0
        self._prox_aviso_meta = time.time() + 600
        self._avisou_empanturrado = False

    # ------------------------------------------------------------------ estado

    @property
    def so_io(self):
        return self.d["so_io"]

    @property
    def ocupado(self):
        return bool(self.trabalhando)

    def meta(self):
        return self.d["meta_semanal"].get("io" if self.so_io else "total")

    def fracao_meta(self):
        """Quanto da meta semanal já foi (0.5 = metade), ou None sem meta/sem contagem."""
        meta = self.meta()
        if not meta or self.semana is None:
            return None
        return tokens.total(self.semana, self.so_io) / meta

    @property
    def empanturrado(self):
        fracao = self.fracao_meta()
        return fracao is not None and fracao >= config.META_EMPANTURRADO

    def mult_energia(self):
        return 1.5 if self.empanturrado else 1.0

    def contar(self, t):
        """Número de tokens pra mostrar, respeitando a opção 'só input e output'."""
        return tokens.total(t, self.so_io) if t else 0

    # ------------------------------------------------------------------ loop

    def tick(self):
        agora = time.time()
        if agora < self._prox_checagem:
            return
        self._prox_checagem = agora + 1
        for evento in self._eventos_novos():
            try:
                self._tratar(evento, agora)
            except Exception:
                log.exception("Erro tratando evento %s", evento)

        # Tokens da semana numa thread (lê arquivos)
        if agora >= self._prox_semana and (self._thread is None or not self._thread.is_alive()):
            self._prox_semana = agora + config.SEGUNDOS_SEMANA
            self._thread = threading.Thread(target=self._contar_semana, daemon=True)
            self._thread.start()

        # Sessões sem notícia há muito tempo param de contar como trabalhando
        limite = agora - config.MINUTOS_TRABALHO_PARADO * 60
        for sessao, quando in list(self.trabalhando.items()):
            if quando < limite:
                del self.trabalhando[sessao]

        self._verificar_espera(agora)
        self._ajustar_acao()
        self._verificar_meta(agora)
        if agora >= self._prox_dias:
            self._prox_dias = agora + 3600
            self._dias_sem_claude(agora)

    def _contar_semana(self):
        try:
            self.semana = self._contador.contar()
        except Exception:
            log.exception("Erro contando tokens da semana")

    def _ler_status(self):
        try:
            return json.loads(self.arq_status.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _eventos_novos(self):
        try:
            tamanho = self.arq_eventos.stat().st_size
        except OSError:
            return []
        if tamanho < self.offset:
            self.offset = 0          # o hook rotacionou o log
        if tamanho == self.offset:
            return []
        with open(self.arq_eventos, "rb") as f:
            f.seek(self.offset)
            bruto = f.read()
        fim = bruto.rfind(b"\n")
        if fim < 0:
            return []
        self.offset += fim + 1
        eventos = []
        for linha in bruto[:fim + 1].decode("utf-8", errors="replace").splitlines():
            try:
                eventos.append(json.loads(linha))
            except ValueError:
                pass
        return eventos

    # ------------------------------------------------------------------ eventos

    def _tratar(self, ev, agora):
        tipo = ev.get("evento")
        sessao = ev.get("session_id") or "?"
        self.d["ultima_atividade"] = ev.get("hora") or datetime.now().astimezone().isoformat()
        self.d["dias_penalizados"] = 0
        if ev.get("tokens_sessao"):
            self.sessao = ev["tokens_sessao"]

        if self.esperando and tipo != "notificacao":
            self.parar_espera()          # o Claude voltou a trabalhar: você respondeu

        if tipo == "prompt":
            self.trabalhando[sessao] = agora
            self._reagir_prompt()
        elif tipo == "fim":
            self.trabalhando.pop(sessao, None)
            self._reagir_fim(ev)
        elif tipo == "notificacao":
            if ev.get("tipo") == "idle_prompt":
                self.trabalhando.pop(sessao, None)
            if ev.get("esperando"):
                self._reagir_espera()
        elif tipo == "teste":
            self.trabalhando[sessao] = agora
            self._reagir_teste(ev.get("passou"))
        elif tipo == "erro":
            self.trabalhando[sessao] = agora
            if agora - self._ultimo_erro > 15:      # não fica reclamando de cada comando
                self._ultimo_erro = agora
                self._reagir_erro()

    def _hoje(self):
        """Resumo do dia no histórico (o resumo do fim do dia usa isso depois)."""
        hist = self.d["historico"]
        hoje = date.today().isoformat()
        corte = (date.today() - timedelta(days=DIAS_HISTORICO)).isoformat()
        for dia in [k for k in hist if k < corte]:
            del hist[dia]
        return hist.setdefault(hoje, {"tasks": 0, "tokens": 0, "testes_ok": 0, "testes_falha": 0,
                                      "erros": 0, "projetos": []})

    # ------------------------------------------------------------------ reações

    def _livre(self):
        """Não interrompe quando ele está no ar (sendo arrastado ou caindo)."""
        return self.m.acao not in ("pendurado", "caindo")

    def _reagir_prompt(self):
        m = self.m
        if m.fase == "ovo":
            m.falar("🍤? Ainda sou um ovo...", 2)
            m.tama.ganhar_xp(config.XP_PROMPT)
            return
        if self.empanturrado:
            if self._livre():
                m.mudar("empanturrado", 3)
            m.falar("Uff... mais tokens?\nTô empanturrado 😪", 2.5)
        else:
            if self._livre():
                m.mudar("comendo", 2.5)
            m._ajustar("fome", config.FOME_PROMPT)
            m.falar(self._frase("prompt", "🍤 Prompt novo! Nham!"), 2)
            m.som_do_pet(especies.especie(m.especie).som_comida)
        m.tama.ganhar_xp(config.XP_PROMPT)

    def _reagir_fim(self, ev):
        m = self.m
        task = ev.get("tokens_task")
        self.ultima_task = task
        dia = self._hoje()
        dia["tasks"] += 1
        dia["tokens"] += self.contar(task)
        if ev.get("projeto") and ev["projeto"] not in dia["projetos"]:
            dia["projetos"].append(ev["projeto"])
        self.d["tasks"] += 1
        self._prox_semana = 0           # recalcula a semana já

        saida = (task or {}).get("saida", 0)
        m.tama.ganhar_xp(config.XP_TASK + min(40, saida // 5000))
        m._ajustar("felicidade", 3)
        texto = f"Terminei! Gastei {tokens.formatar(self.contar(task))} tokens" if task else "Terminei!"
        fracao = self.fracao_meta()
        if fracao is not None and fracao >= 1:
            texto += "\n(passou da meta da semana 🛌)"
        if self._livre():
            m.mudar("comemorando", 3)
        m.falar(texto + " 🎉", 4)
        self._som("fim")

    def _reagir_espera(self):
        self.esperando = time.time()
        m = self.m
        if self._livre():
            m.mudar("acenando")          # sem prazo: acena até você voltar
        m.falar("Preciso de você! 🙋", fixo=True)
        self._som("chamando")

    def parar_espera(self):
        if self.esperando is None:
            return
        self.esperando = None
        if self.m.acao == "acenando":
            self.m.mudar("parado", 1.5)
        if self.m.balao.texto.startswith("Preciso de você"):
            self.m.balao.esconder()

    def _reagir_teste(self, passou):
        m = self.m
        dia = self._hoje()
        if passou:
            dia["testes_ok"] += 1
            m.tama.ganhar_xp(config.XP_TESTE_OK)
            if self._livre():
                m.mudar("comemorando", 2.5)
            m.falar("Testes passando! ✅", 2)
            self._som("ok")
        else:
            dia["testes_falha"] += 1
            if self._livre():
                m.mudar("caido", 4)
            m.falar(self._frase("teste_falhou", "💀 Os testes falharam..."), 3)
            self._som("triste")

    def _reagir_erro(self):
        self._hoje()["erros"] += 1
        if self._livre():
            self.m.mudar("mao_na_cabeca", 2.5)
        self.m.falar(self._frase("erro", "Ops! Deu erro no terminal 🤦"), 2.5)

    def _frase(self, chave, padrao):
        """Fala do jeito do pet (o patinho de borracha, por exemplo, pede pra você explicar o bug)."""
        return especies.especie(self.m.especie).frases.get(chave, padrao)

    def _som(self, nome):
        if self.d["sons"]:
            sons.tocar(nome)

    # ------------------------------------------------------------------ rotinas

    def _ajustar_acao(self):
        """Digitando enquanto o Claude trabalha; acenando enquanto ele espera você."""
        m = self.m
        if m.fase == "ovo":
            return
        if self.esperando:
            if m.acao in ("parado", "andando", "digitando"):
                m.mudar("acenando")
                m.falar("Preciso de você! 🙋", fixo=True)
            return
        if self.ocupado and m.acao in ("parado", "andando"):
            m.mudar("digitando")
        elif not self.ocupado and m.acao == "digitando":
            m.mudar("parado", 2)

    def _verificar_espera(self, agora):
        """Para de acenar quando você volta pro terminal e mexe em alguma coisa."""
        if self.esperando is None:
            return
        if agora - self.esperando > config.MINUTOS_ESPERA_MAX * 60:
            self.parar_espera()
            return
        voltou = tela.programa_em_primeiro_plano() in config.TERMINAIS
        mexeu_depois = tela.segundos_ocioso() < agora - self.esperando
        if voltou and mexeu_depois:
            self.parar_espera()

    def _verificar_meta(self, agora):
        fracao = self.fracao_meta()
        if fracao is None or not self.m.tama.ativo:
            return
        if fracao >= config.META_EMPANTURRADO and not self._avisou_empanturrado:
            self._avisou_empanturrado = True
            if fracao < 1:
                self.m.falar("Uff, comi muito token essa semana... 😪", 3)
        if (fracao >= 1 and agora >= self._prox_aviso_meta and not self.ocupado
                and not self.m.balao.visivel and tela.segundos_ocioso() < 120):
            self._prox_aviso_meta = agora + 1800
            self.m.falar("Passou da meta da semana! 🛌\nQue tal descansar um pouco?", 5)

    def _dias_sem_claude(self, agora):
        """Cada dia inteiro sem Claude deixa ele com fome e tristinho (uma vez por dia)."""
        ultima = max(_epoch(self.d.get("ultima_atividade")), self._contador.ultima_atividade)
        if not ultima or not self.m.tama.ativo:
            return
        dias = int((agora - ultima) // 86400)
        novos = dias - self.d["dias_penalizados"]
        if dias >= 1 and novos > 0:
            self.d["dias_penalizados"] = dias
            self.m.estado.ajustar_status("fome", -10 * novos)
            self.m.estado.ajustar_status("felicidade", -10 * novos)
            plural = "dia" if dias == 1 else "dias"
            self.m.falar(f"Faz {dias} {plural} que você\nnão usa o Claude... 🥺", 4)

    # ------------------------------------------------------------------ opções do menu

    def alternar_so_io(self, valor):
        self.d["so_io"] = valor
        self._avisou_empanturrado = False
        modo = "só input + output" if valor else "tudo, com cache"
        self.m.falar(f"Contando tokens: {modo}", 2)

    def definir_meta(self, valor):
        self.d["meta_semanal"]["io" if self.so_io else "total"] = valor
        self._avisou_empanturrado = False
        self.m.falar(f"Meta semanal: {tokens.formatar(valor)} tokens" if valor else "Sem meta semanal", 2)
