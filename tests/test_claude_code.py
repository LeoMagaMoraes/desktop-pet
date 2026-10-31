"""Reações do Clawd aos eventos do Claude Code (com o mascote de verdade e um ~/.claude de mentira)."""

import json
import time
import unittest
from datetime import datetime, timedelta

from tests.test_mascote import BaseMascote

TASK = {"entrada": 100, "saida": 12_000, "cache_criacao": 5_000, "cache_leitura": 200_000}


class TestClaudeCode(BaseMascote):
    def tick(self):
        self.m.cc._prox_checagem = 0
        self.m.cc.tick()

    def test_prompt_vira_comida_e_ele_digita(self):
        m = self.m
        m.estado.status["fome"] = 50
        self.hook(evento="prompt", tokens_sessao=TASK)
        self.assertEqual(m.acao, "comendo")
        self.assertEqual(m.estado.status["fome"], 60)
        self.assertIn("Prompt novo", m.balao.texto)
        self.assertTrue(m.cc.ocupado)
        m.mudar("parado", 10)
        self.tick()
        self.assertEqual(m.acao, "digitando")

    def test_fim_comemora_e_conta_os_tokens(self):
        m = self.m
        xp = m.estado.dados["xp"]
        self.hook(evento="prompt")
        self.hook(evento="fim", tokens_task=TASK, tokens_sessao=TASK, projeto="meuapp")
        self.assertEqual(m.acao, "comemorando")
        self.assertIn("Terminei! Gastei 217.1k tokens", m.balao.texto)
        self.assertFalse(m.cc.ocupado)
        self.assertEqual(m.estado.dados["xp"], xp + 2 + 10 + 2)    # prompt + task + bônus da saída
        dia = list(m.estado.dados["claude"]["historico"].values())[0]
        self.assertEqual((dia["tasks"], dia["projetos"]), (1, ["meuapp"]))
        self.assertEqual(m.cc.sessao, TASK)

    def test_so_input_e_output(self):
        self.m.cc.alternar_so_io(True)
        self.hook(evento="fim", tokens_task=TASK)
        self.assertIn("Gastei 12.1k tokens", self.m.balao.texto)

    def test_fim_sem_tokens(self):
        self.hook(evento="fim", tokens_task=None)
        self.assertTrue(self.m.balao.texto.startswith("Terminei!"))

    def test_notificacao_acena_ate_voltar(self):
        m = self.m
        self.hook(evento="notificacao", esperando=True, tipo="permission_prompt")
        self.assertEqual(m.acao, "acenando")
        self.assertIsNone(m.acao_ate)                    # acena sem parar
        self.assertIn("Preciso de você", m.balao.texto)
        m.mudar("parado", 5)                             # se ele parar, volta a acenar
        self.tick()
        self.assertEqual(m.acao, "acenando")
        self.clicar()                                    # clicar nele também vale como "voltei"
        self.assertIsNone(m.cc.esperando)
        self.assertNotEqual(m.acao, "acenando")

    def test_novo_evento_tambem_para_de_acenar(self):
        self.hook(evento="notificacao", esperando=True)
        self.hook(evento="teste", passou=True)
        self.assertIsNone(self.m.cc.esperando)

    def test_notificacao_que_nao_pede_nada_nao_acena(self):
        self.hook(evento="notificacao", esperando=False, tipo="auth_success")
        self.assertNotEqual(self.m.acao, "acenando")

    def test_testes(self):
        m = self.m
        self.hook(evento="teste", passou=True)
        self.assertEqual(m.acao, "comemorando")
        self.hook(evento="teste", passou=False)
        self.assertEqual(m.acao, "caido")
        self.assertIn("💀", m.balao.texto)

    def test_erro_no_terminal(self):
        m = self.m
        self.hook(evento="erro", comando="git psuh", codigo=1)
        self.assertEqual(m.acao, "mao_na_cabeca")
        m.mudar("parado", 10)
        self.hook(evento="erro", comando="git psuh", codigo=1)
        # Não reclama de novo logo em seguida; o Claude segue trabalhando, então ele volta a digitar
        self.assertEqual(m.acao, "digitando")

    def test_nao_interrompe_quem_esta_no_ar(self):
        self.m.mudar("caindo")
        self.hook(evento="teste", passou=False)
        self.assertEqual(self.m.acao, "caindo")

    def test_meta_semanal(self):
        m = self.m
        m.cc.definir_meta(1_000_000)
        m.cc.semana = {"entrada": 0, "saida": 0, "cache_criacao": 0, "cache_leitura": 850_000}
        self.assertTrue(m.cc.empanturrado)
        self.assertEqual(m.cc.mult_energia(), 1.5)
        self.hook(evento="prompt")
        self.assertEqual(m.acao, "empanturrado")
        m.cc.semana["cache_leitura"] = 1_200_000
        self.hook(evento="fim", tokens_task=TASK)
        self.assertIn("passou da meta", m.balao.texto)
        m.cc.definir_meta(None)
        self.assertFalse(m.cc.empanturrado)

    def test_dias_sem_claude(self):
        m = self.m
        tres_dias = (datetime.now().astimezone() - timedelta(days=3, hours=1)).isoformat()
        m.estado.dados["claude"]["ultima_atividade"] = tres_dias
        m.estado.status.update(fome=80, felicidade=80)
        m.cc._dias_sem_claude(time.time())
        self.assertEqual((m.estado.status["fome"], m.estado.status["felicidade"]), (50, 50))
        self.assertIn("3 dias", m.balao.texto)
        m.cc._dias_sem_claude(time.time())               # não desconta duas vezes
        self.assertEqual(m.estado.status["fome"], 50)

    def test_painel_com_tokens(self):
        m = self.m
        m.cc.semana = dict(TASK)
        m.cc.sessao = dict(TASK)
        m.cc.ultima_task = dict(TASK)
        m.mostrar_status()
        m.root.update()
        c = m.painel.canvas
        textos = " ".join(c.itemcget(i, "text") for i in c.find_all() if c.type(i) == "text")
        self.assertIn("Últimos 7 dias", textos)
        self.assertIn("não o limite", textos)
        self.assertIn("217.1k / 150.0M", textos)

    def test_ovo_nao_digita(self):
        m = self.m
        m.fase = "ovo"
        self.hook(evento="prompt")
        m.mudar("parado", 10)
        self.tick()
        self.assertEqual(m.acao, "parado")


class TestEventosAntigos(BaseMascote):
    def antes_de_criar(self):
        (self.claude / "clawd-eventos.jsonl").write_text(json.dumps({"evento": "fim"}) + "\n",
                                                          encoding="utf-8")

    def test_ignora_o_que_aconteceu_antes_de_abrir(self):
        self.m.cc._prox_checagem = 0
        self.m.cc.tick()
        self.assertEqual(self.m.estado.dados["claude"]["tasks"], 0)
        self.hook(evento="fim")
        self.assertEqual(self.m.estado.dados["claude"]["tasks"], 1)


if __name__ == "__main__":
    unittest.main()
