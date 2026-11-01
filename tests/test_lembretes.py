"""Lembretes: entender o "quando" em português e o pet avisando na hora."""

import time
import unittest
from datetime import datetime, timedelta

from pet import lembretes as lb
from tests.test_mascote import BaseMascote

# Quarta-feira, 4/11/2026, 10:00
AGORA = datetime(2026, 11, 4, 10, 0)


def quando(texto, agora=AGORA):
    return lb.interpretar(texto, agora)[0]


class TestInterpretar(unittest.TestCase):
    def test_agora_e_quarta(self):
        self.assertEqual(AGORA.weekday(), 2)

    def test_relativos(self):
        self.assertEqual(quando("daqui a 20 min"), AGORA + timedelta(minutes=20))
        self.assertEqual(quando("em 2 horas"), AGORA + timedelta(hours=2))
        self.assertEqual(quando("30min"), AGORA + timedelta(minutes=30))
        self.assertEqual(quando("em 1h30"), AGORA + timedelta(minutes=90))
        self.assertEqual(quando("daqui a 2h"), AGORA + timedelta(hours=2))
        self.assertEqual(quando("1 hora e 15 minutos"), AGORA + timedelta(minutes=75))
        self.assertEqual(quando("daqui 3 dias"), AGORA + timedelta(days=3))

    def test_relativo_ignora_segundos(self):
        self.assertEqual(quando("10 min", datetime(2026, 11, 4, 10, 0, 42)), datetime(2026, 11, 4, 10, 10))

    def test_so_hora_hoje_ou_amanha(self):
        self.assertEqual(quando("15:30"), datetime(2026, 11, 4, 15, 30))
        self.assertEqual(quando("às 15"), datetime(2026, 11, 4, 15, 0))
        self.assertEqual(quando("15h"), datetime(2026, 11, 4, 15, 0))
        self.assertEqual(quando("15h45"), datetime(2026, 11, 4, 15, 45))
        self.assertEqual(quando("11h30"), datetime(2026, 11, 4, 11, 30))   # sem "em": é horário
        self.assertEqual(quando("meio-dia"), datetime(2026, 11, 4, 12, 0))
        # Já passou hoje: fica pra amanhã
        self.assertEqual(quando("8:00"), datetime(2026, 11, 5, 8, 0))
        self.assertEqual(quando("meia-noite"), datetime(2026, 11, 5, 0, 0))

    def test_dias_por_nome(self):
        self.assertEqual(quando("amanhã 9h"), datetime(2026, 11, 5, 9, 0))
        self.assertEqual(quando("amanha"), datetime(2026, 11, 5, lb.HORA_PADRAO, 0))
        self.assertEqual(quando("depois de amanhã às 14"), datetime(2026, 11, 6, 14, 0))
        self.assertEqual(quando("hoje 18:00"), datetime(2026, 11, 4, 18, 0))

    def test_dia_da_semana(self):
        self.assertEqual(quando("sexta 14h"), datetime(2026, 11, 6, 14, 0))
        self.assertEqual(quando("segunda às 8"), datetime(2026, 11, 9, 8, 0))
        self.assertEqual(quando("sábado"), datetime(2026, 11, 7, lb.HORA_PADRAO, 0))
        # Quarta: mais tarde hoje vale; mais cedo pula pra semana que vem
        self.assertEqual(quando("quarta 16h"), datetime(2026, 11, 4, 16, 0))
        self.assertEqual(quando("quarta 8h"), datetime(2026, 11, 11, 8, 0))

    def test_data(self):
        self.assertEqual(quando("25/12 8h"), datetime(2026, 12, 25, 8, 0))
        self.assertEqual(quando("25/12/2027 às 10"), datetime(2027, 12, 25, 10, 0))
        self.assertEqual(quando("5/1/27 9:15"), datetime(2027, 1, 5, 9, 15))
        # Data sem ano que já passou: ano que vem
        self.assertEqual(quando("1/3 9h"), datetime(2027, 3, 1, 9, 0))

    def test_todo_dia(self):
        q, repetir = lb.interpretar("todo dia 9h", AGORA)
        self.assertEqual((q, repetir), (datetime(2026, 11, 5, 9, 0), "diario"))
        q, repetir = lb.interpretar("todos os dias às 18:30", AGORA)
        self.assertEqual((q, repetir), (datetime(2026, 11, 4, 18, 30), "diario"))

    def test_nao_entende(self):
        for texto in ("", "   ", "qualquer hora", "31/02 9h", "25:00", "ontem", "1/1/2020 9h", "hoje 8h"):
            self.assertEqual(lb.interpretar(texto, AGORA), (None, None), texto)

    def test_formatar(self):
        self.assertEqual(lb.formatar(datetime(2026, 11, 4, 15, 30), AGORA), "hoje às 15:30")
        self.assertEqual(lb.formatar(datetime(2026, 11, 5, 9, 0), AGORA), "amanhã às 09:00")
        self.assertEqual(lb.formatar(datetime(2026, 11, 7, 14, 0), AGORA), "sábado (07/11) às 14:00")
        self.assertEqual(lb.formatar(datetime(2026, 12, 25, 8, 0), AGORA), "25/12 às 08:00")
        self.assertEqual(lb.formatar(datetime(2027, 1, 5, 8, 0), AGORA), "05/01/2027 às 08:00")
        self.assertEqual(lb.formatar(datetime(2026, 11, 5, 9, 0), AGORA, "diario"), "todo dia às 09:00")

    def test_valido(self):
        bom = lb.novo("Beber água", AGORA)
        self.assertTrue(lb.valido(bom))
        self.assertFalse(lb.valido({**bom, "quando": "ontem"}))
        self.assertFalse(lb.valido({**bom, "texto": ""}))
        self.assertFalse(lb.valido({"id": "x"}))


class TestLembretesNoPet(BaseMascote):
    def antes_de_criar(self):
        from tests import test_mascote
        passou = (datetime.now() - timedelta(hours=1)).isoformat(timespec="minutes")
        self.SAVE = {**test_mascote.BaseMascote.SAVE, "lembretes": [
            {"id": "velho", "texto": "Ligar pro dentista", "quando": passou, "repetir": None},
            {"id": "ruim", "texto": "Estragado", "quando": "não é data"},
        ]}

    def disparar(self):
        self.m.lembretes._prox_checagem = 0
        self.m.lembretes.tick()

    def test_save_estragado_e_descartado(self):
        self.assertEqual([l["id"] for l in self.m.lembretes.lista], ["velho"])

    def test_espera_o_oi_antes_de_avisar(self):
        self.m.lembretes.tick()
        self.assertIsNone(self.m.lembretes.ativo)

    def test_atrasado_avisa_ao_abrir_e_clique_dispensa(self):
        m = self.m
        self.disparar()
        self.assertEqual(m.lembretes.ativo["id"], "velho")
        self.assertEqual(m.acao, "acenando")
        self.assertIn("Ligar pro dentista", m.balao.texto)
        self.assertIn("era pra", m.balao.texto)            # o PC tava desligado na hora
        self.assertEqual(m.lembretes.lista, [])            # único: sai da lista
        self.assertEqual(m.estado.carregar(m.estado.caminho).dados["lembretes"], [])   # e do save
        # Continua acenando até alguém ver
        m.mudar("parado", 1)
        self.disparar()
        self.assertEqual(m.acao, "acenando")
        felicidade = m.estado.status["felicidade"]
        self.clicar()
        self.assertIsNone(m.lembretes.ativo)
        self.assertEqual(m.balao.texto, "Beleza! ✅")
        self.assertEqual(m.estado.status["felicidade"], felicidade)   # o clique foi o "vi", não carinho

    def test_acorda_pra_avisar(self):
        self.m.dormir()
        self.disparar()
        self.assertEqual(self.m.acao, "acenando")

    def test_adiar(self):
        m = self.m
        self.disparar()
        m.lembretes.adiar()
        self.assertIsNone(m.lembretes.ativo)
        [adiado] = m.lembretes.lista
        self.assertEqual(adiado["texto"], "Ligar pro dentista")
        faltam = lb.quando_de(adiado) - datetime.now()
        self.assertTrue(timedelta(minutes=9) < faltam <= timedelta(minutes=10))
        self.assertIn("de novo", m.balao.texto)

    def test_diario_reagenda(self):
        m = self.m
        m.lembretes.lista.clear()
        tres_dias = (datetime.now() - timedelta(days=3, minutes=5)).replace(second=0, microsecond=0)
        m.lembretes.lista.append(lb.novo("Remédio", tres_dias, "diario"))
        self.disparar()
        self.assertEqual(m.lembretes.ativo["texto"], "Remédio")
        [proximo] = m.lembretes.lista
        q = lb.quando_de(proximo)
        self.assertGreater(q, datetime.now())
        self.assertLessEqual(q - datetime.now(), timedelta(days=1))
        self.assertEqual((q.hour, q.minute), (tres_dias.hour, tres_dias.minute))

    def test_futuro_nao_dispara(self):
        m = self.m
        m.lembretes.lista.clear()
        m.lembretes.adicionar("Reunião", datetime.now() + timedelta(minutes=5))
        self.assertIn("Combinado", m.balao.texto)
        self.disparar()
        self.assertIsNone(m.lembretes.ativo)

    def test_menu_mostra_feito_e_adiar_quando_tocando(self):
        self.disparar()
        self.abrir_menu()
        textos = self.textos_do_menu()
        self.assertIn("Feito!", textos)
        self.assertIn(f"Me lembra em {lb.ADIAR_MINUTOS} min", textos)
        self.clicar_no_menu("Feito!")
        self.esperar(lambda: self.m.lembretes.ativo is None)
        self.assertIsNone(self.m.lembretes.ativo)

    def test_pagina_lista_e_apaga(self):
        m = self.m
        m.lembretes.lista.clear()
        m.lembretes.adicionar("Regar as plantas", datetime.now() + timedelta(days=1))
        self.abrir_menu()
        self.assertIn("1  ›", self.textos_do_menu())
        self.clicar_no_menu("Lembretes")
        textos = self.textos_do_menu()
        self.assertIn("Novo lembrete", textos)
        self.assertIn("Regar as plantas", textos)
        self.clicar_no_menu("Regar as plantas")
        self.assertEqual(m.lembretes.lista, [])
        self.assertNotIn("Regar as plantas", self.textos_do_menu())

    def test_dialogo_cria_lembrete(self):
        m = self.m
        m.lembretes.lista.clear()
        d = m.dialogo_lembrete
        d.abrir()
        d.texto.insert(0, "Alongar")
        d.quando.insert(0, "daqui a 15 min")
        d._atualizar_previa()
        self.assertTrue(d.previa.cget("text").startswith("→ hoje às") or "amanhã" in d.previa.cget("text"))
        d._salvar()
        self.assertFalse(d.aberto)
        [l] = m.lembretes.lista
        self.assertEqual(l["texto"], "Alongar")

    def test_dialogo_nao_aceita_horario_estranho(self):
        d = self.m.dialogo_lembrete
        d.abrir()
        d.texto.insert(0, "Alongar")
        d.quando.insert(0, "qualquer hora")
        d._salvar()
        self.assertTrue(d.aberto)
        self.assertIn("Não entendi", d.previa.cget("text"))
        d.fechar()


if __name__ == "__main__":
    unittest.main()
