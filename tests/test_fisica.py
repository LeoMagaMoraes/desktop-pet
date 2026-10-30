import unittest

from clawd.fisica import Corpo, Limites, Parametros, limitar_velocidade, passo

LIM = Limites(esquerda=0, direita=1000, topo=0, chao=800, meia_largura=40, altura=60)
P = Parametros()


def simular(corpo, segundos=10, dt=1 / 30):
    """Roda a física até pousar; devolve todos os eventos."""
    eventos = []
    for _ in range(int(segundos / dt)):
        novos = passo(corpo, LIM, P, dt)
        eventos += novos
        if any(n == "pousou" for n, _ in novos):
            break
    return eventos


class TestFisica(unittest.TestCase):
    def test_queda_livre_pousa_no_chao(self):
        c = Corpo(500, 200)
        eventos = simular(c)
        self.assertEqual(eventos[-1][0], "pousou")
        self.assertEqual(c.y, LIM.chao)
        self.assertEqual((c.vx, c.vy), (0, 0))

    def test_queda_alta_quica_antes_de_pousar(self):
        c = Corpo(500, 100)
        nomes = [n for n, _ in simular(c)]
        self.assertIn("quique", nomes)

    def test_quique_perde_velocidade(self):
        c = Corpo(500, 100)
        quiques = [v for n, v in simular(c) if n == "quique"]
        self.assertTrue(all(b < a for a, b in zip(quiques, quiques[1:])))

    def test_arremesso_bate_na_parede_direita_e_volta(self):
        c = Corpo(800, 400, vx=3000, vy=-500)
        eventos = simular(c)
        self.assertIn("parede", [n for n, _ in eventos])
        self.assertLessEqual(c.x + LIM.meia_largura, LIM.direita)

    def test_parede_inverte_e_amortece(self):
        c = Corpo(955, 400, vx=1000)
        eventos = passo(c, LIM, P, 0.01)
        self.assertEqual(eventos[0][0], "parede")
        self.assertAlmostEqual(c.vx, -1000 * P.quique_parede)

    def test_teto(self):
        c = Corpo(500, 70, vy=-2000)
        eventos = passo(c, LIM, P, 0.02)
        self.assertEqual(eventos[0][0], "teto")
        self.assertGreater(c.vy, 0)
        self.assertEqual(c.y, LIM.topo + LIM.altura)

    def test_escorrega_e_para(self):
        c = Corpo(500, LIM.chao, vx=600, no_chao=True)
        eventos = simular(c)
        self.assertEqual(eventos[-1][0], "pousou")
        self.assertGreater(c.x, 500)

    def test_nunca_sai_da_tela(self):
        c = Corpo(500, 400, vx=-4500, vy=-4500)
        for _ in range(300):
            passo(c, LIM, P, 1 / 30)
            self.assertGreaterEqual(c.x - LIM.meia_largura, LIM.esquerda)
            self.assertLessEqual(c.x + LIM.meia_largura, LIM.direita)
            self.assertLessEqual(c.y, LIM.chao)
            self.assertGreaterEqual(c.y - LIM.altura, LIM.topo)

    def test_limitar_velocidade(self):
        self.assertEqual(limitar_velocidade(30, 40, 100), (30, 40))
        vx, vy = limitar_velocidade(300, 400, 100)
        self.assertAlmostEqual(vx, 60)
        self.assertAlmostEqual(vy, 80)
        self.assertEqual(limitar_velocidade(0, 0, 100), (0, 0))


if __name__ == "__main__":
    unittest.main()
