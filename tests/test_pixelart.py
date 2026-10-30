import unittest

from clawd import pixelart as p

ANIMACOES_PEDIDAS = {"parado", "andando", "dormindo", "pendurado", "caindo",
                     "comendo", "comemorando", "acenando", "escondido"}


class TestPixelArt(unittest.TestCase):
    def test_todas_as_animacoes_existem(self):
        self.assertTrue(ANIMACOES_PEDIDAS <= set(p.ANIMACOES))

    def test_quadros_tem_o_tamanho_da_grade(self):
        for nome, (ms, quadros) in p.ANIMACOES.items():
            self.assertGreater(ms, 0, nome)
            self.assertTrue(quadros, nome)
            for g in quadros:
                self.assertEqual((g.largura, g.altura), (p.LARGURA, p.ALTURA), nome)
                self.assertGreater(g.pixels_pintados(), 10, nome)

    def test_em_pe_encosta_no_chao(self):
        # Os pés precisam tocar a última linha pra ele não flutuar sobre a barra
        for nome in ("parado", "andando", "comendo", "comemorando", "acenando", "tonto"):
            for g in p.ANIMACOES[nome][1]:
                self.assertTrue(any(g.px[-1]), nome)

    def test_parado_e_simetrico(self):
        g = p.ANIMACOES["parado"][1][0]
        for linha in g.px:
            self.assertEqual(linha, linha[::-1])

    def test_escondido_so_mostra_o_topo(self):
        for g in p.ANIMACOES["escondido"][1]:
            self.assertFalse(any(any(linha) for linha in g.px[:p.ALTURA - 4]))

    def test_desenho_fora_da_grade_e_ignorado(self):
        g = p.Grade(3, 3)
        g.retangulo(-5, -5, 10, 10, "#000000")
        self.assertEqual(g.pixels_pintados(), 9)

    def test_efeitos(self):
        for nome in ("coracao", "estrela", "zzz", "migalha"):
            self.assertGreater(p.EFEITOS[nome].pixels_pintados(), 0)


if __name__ == "__main__":
    unittest.main()
