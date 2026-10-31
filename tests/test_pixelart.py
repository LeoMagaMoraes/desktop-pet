import unittest

from clawd import pixelart as p

ANIMACOES_PEDIDAS = {"parado", "andando", "dormindo", "pendurado", "caindo",
                     "comendo", "comemorando", "acenando", "escondido"}


class TestPixelArt(unittest.TestCase):
    def test_todas_as_fases_tem_as_animacoes(self):
        for fase in p.FASES:
            self.assertTrue(ANIMACOES_PEDIDAS <= set(p.animacoes(fase)), fase)

    def test_quadros_tem_o_tamanho_da_grade(self):
        for fase in p.FASES:
            for nome, (ms, quadros) in p.animacoes(fase).items():
                self.assertGreater(ms, 0, nome)
                self.assertTrue(quadros, nome)
                for g in quadros:
                    self.assertEqual((g.largura, g.altura), (p.LARGURA, p.ALTURA), f"{fase}/{nome}")
                    self.assertGreater(g.pixels_pintados(), 10, f"{fase}/{nome}")

    def test_em_pe_encosta_no_chao(self):
        # Os pés precisam tocar a última linha pra ele não flutuar sobre a barra
        for fase in p.FASES:
            an = p.animacoes(fase)
            for nome in ("parado", "andando", "comendo", "comemorando", "acenando", "tonto"):
                for g in an[nome][1]:
                    self.assertTrue(any(g.px[-1]), f"{fase}/{nome}")

    def test_parado_e_simetrico(self):
        for fase in ("filhote", "clawd", "anciao"):
            g = p.animacoes(fase)["parado"][1][0]
            for linha in g.px:
                self.assertEqual(linha, linha[::-1], fase)

    def test_escondido_so_mostra_o_topo(self):
        for fase in ("ovo", "filhote", "clawd"):
            for g in p.animacoes(fase)["escondido"][1]:
                self.assertFalse(any(any(linha) for linha in g.px[:p.ALTURA - 4]), fase)

    def test_filhote_e_menor_que_o_clawd(self):
        self.assertLess(p.animacoes("filhote")["parado"][1][0].pixels_pintados(),
                        p.animacoes("clawd")["parado"][1][0].pixels_pintados())

    def test_anciao_tem_cartola_oculos_e_barba(self):
        cores = {c for linha in p.animacoes("anciao")["parado"][1][0].px for c in linha}
        self.assertTrue({p.FITA, p.ARMACAO, p.BARBA} <= cores)
        # A cartola fica acima do corpo
        g = p.animacoes("anciao")["parado"][1][0]
        self.assertTrue(any(g.px[0]))

    def test_so_o_ovo_choca(self):
        self.assertIn("chocando", p.animacoes("ovo"))
        self.assertNotIn("chocando", p.animacoes("clawd"))

    def test_medidas(self):
        self.assertEqual(p.medidas("clawd"), (11, 9))
        self.assertLess(p.medidas("filhote")[0], p.medidas("clawd")[0])

    def test_desenho_fora_da_grade_e_ignorado(self):
        g = p.Grade(3, 3)
        g.retangulo(-5, -5, 10, 10, "#000000")
        self.assertEqual(g.pixels_pintados(), 9)

    def test_efeitos(self):
        for nome in ("coracao", "estrela", "zzz", "migalha", "mosca", "bolha", "gota"):
            self.assertGreater(p.EFEITOS[nome].pixels_pintados(), 0)


if __name__ == "__main__":
    unittest.main()
