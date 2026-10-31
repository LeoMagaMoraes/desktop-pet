import copy
import unittest

from clawd import necessidades as n
from clawd.estado import PADRAO


def dados(**status):
    d = copy.deepcopy(PADRAO)
    d["status"].update(status)
    return d


class TestFases(unittest.TestCase):
    def test_fase_por_xp(self):
        self.assertEqual(n.fase_por_xp(0), "ovo")
        self.assertEqual(n.fase_por_xp(99), "ovo")
        self.assertEqual(n.fase_por_xp(100), "filhote")
        self.assertEqual(n.fase_por_xp(999), "filhote")
        self.assertEqual(n.fase_por_xp(1000), "clawd")
        self.assertEqual(n.fase_por_xp(10000), "anciao")
        self.assertEqual(n.fase_por_xp(10 ** 9), "anciao")

    def test_proxima_fase(self):
        self.assertEqual(n.proxima_fase(0), ("filhote", 100))
        self.assertEqual(n.proxima_fase(150), ("clawd", 1000))
        self.assertIsNone(n.proxima_fase(10000))


class TestPassarTempo(unittest.TestCase):
    def test_acordado_uma_hora(self):
        d = dados(fome=80, energia=80, felicidade=80)
        n.passar_tempo(d, 1)
        t = n.TAXAS
        self.assertAlmostEqual(d["status"]["fome"], 80 - t.fome_acordado)
        self.assertAlmostEqual(d["status"]["energia"], 80 - t.energia_acordado)
        self.assertAlmostEqual(d["status"]["felicidade"], 80 - t.felicidade_presente)
        self.assertAlmostEqual(d["sujeira"], t.sujeira_acordado)

    def test_dormindo_recupera_energia(self):
        d = dados(energia=20)
        n.passar_tempo(d, 1, dormindo=True)
        self.assertAlmostEqual(d["status"]["energia"], 20 + n.TAXAS.energia_dormindo)

    def test_sozinho_fica_triste_mais_rapido(self):
        perto, longe = dados(), dados()
        n.passar_tempo(perto, 1)
        n.passar_tempo(longe, 1, sozinho=True)
        self.assertLess(longe["status"]["felicidade"], perto["status"]["felicidade"])

    def test_limites_0_a_100(self):
        d = dados(fome=1, energia=99)
        n.passar_tempo(d, 50, dormindo=True)
        self.assertEqual(d["status"]["fome"], 0)
        self.assertEqual(d["status"]["energia"], 100)
        self.assertLessEqual(d["sujeira"], 100)

    def test_fome_prolongada_deixa_gripado(self):
        d = dados(fome=10)
        self.assertEqual(n.passar_tempo(d, 1), [])
        self.assertFalse(d["doente"])
        self.assertEqual(n.passar_tempo(d, 1.1), ["ficou_doente"])
        self.assertTrue(d["doente"])
        self.assertEqual(n.passar_tempo(d, 1), [])          # avisa uma vez só

    def test_comer_zera_contador_de_fome(self):
        d = dados(fome=10)
        n.passar_tempo(d, 1.5)
        d["status"]["fome"] = 60
        n.passar_tempo(d, 0.01)
        self.assertEqual(d["horas_com_fome"], 0)

    def test_gripado_gasta_mais_energia(self):
        sao, doente = dados(), dados()
        doente["doente"] = True
        n.passar_tempo(sao, 1)
        n.passar_tempo(doente, 1)
        self.assertLess(doente["status"]["energia"], sao["status"]["energia"])


class TestOffline(unittest.TestCase):
    def test_uma_noite(self):
        d = dados(fome=80, energia=30, felicidade=80)
        n.simular_offline(d, 8)
        self.assertAlmostEqual(d["status"]["fome"], 80 - 8 * n.TAXAS.fome_offline, places=3)
        self.assertEqual(d["status"]["energia"], 100)        # dormiu a noite toda
        self.assertFalse(d["doente"])

    def test_fim_de_semana_fora_deixa_gripado(self):
        d = dados(fome=80)
        eventos = n.simular_offline(d, 60)
        self.assertEqual(d["status"]["fome"], 0)
        self.assertTrue(d["doente"])
        self.assertIn("ficou_doente", eventos)

    def test_zero_horas_nao_muda_nada(self):
        d = dados()
        antes = copy.deepcopy(d)
        n.simular_offline(d, 0)
        self.assertEqual(d, antes)


class TestFormatar(unittest.TestCase):
    def test_formatos(self):
        self.assertEqual(n.formatar_duracao(0.25), "15 min")
        self.assertEqual(n.formatar_duracao(1.5), "1h30")
        self.assertEqual(n.formatar_duracao(3), "3h")
        self.assertEqual(n.formatar_duracao(1.999), "2h")
        self.assertEqual(n.formatar_duracao(50), "2 dias")


if __name__ == "__main__":
    unittest.main()
