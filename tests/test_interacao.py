import unittest

from pet.interacao import DetectorSacudida, eh_arrasto, estimar_velocidade


class TestCliqueOuArrasto(unittest.TestCase):
    def test_menos_de_5_pixels_e_clique(self):
        self.assertFalse(eh_arrasto((100, 100), (103, 103)))   # ~4,2 px
        self.assertFalse(eh_arrasto((100, 100), (100, 100)))

    def test_5_pixels_ou_mais_e_arrasto(self):
        self.assertTrue(eh_arrasto((100, 100), (105, 100)))
        self.assertTrue(eh_arrasto((100, 100), (103, 104)))    # exatamente 5


class TestVelocidade(unittest.TestCase):
    def test_movimento_constante(self):
        amostras = [(i * 0.016, i * 16, -i * 8) for i in range(10)]
        vx, vy = estimar_velocidade(amostras, agora=amostras[-1][0] + 0.005)
        self.assertAlmostEqual(vx, 1000, delta=1)
        self.assertAlmostEqual(vy, -500, delta=1)

    def test_parou_antes_de_soltar_nao_arremessa(self):
        amostras = [(i * 0.016, i * 16, 0) for i in range(10)]
        self.assertEqual(estimar_velocidade(amostras, agora=amostras[-1][0] + 0.3), (0, 0))

    def test_usa_so_o_finalzinho(self):
        # Foi pra direita devagar e no fim pra esquerda rápido: vale o fim
        amostras = [(i * 0.02, i * 2, 0) for i in range(20)]
        t, x = amostras[-1][0], amostras[-1][1]
        amostras += [(t + i * 0.016, x - i * 30, 0) for i in range(1, 6)]
        vx, _ = estimar_velocidade(amostras, agora=amostras[-1][0])
        self.assertLess(vx, -1000)

    def test_amostra_unica(self):
        self.assertEqual(estimar_velocidade([(0, 0, 0)], agora=0), (0, 0))


class TestSacudida(unittest.TestCase):
    def chacoalhar(self, det, vezes, intervalo, amplitude=80):
        resultado = False
        x = 0
        for i in range(vezes):
            x = amplitude if i % 2 == 0 else 0
            resultado = det.adicionar(i * intervalo, x, 0) or resultado
        return resultado

    def test_chacoalhar_rapido_deixa_tonto(self):
        self.assertTrue(self.chacoalhar(DetectorSacudida(), 10, 0.08))

    def test_chacoalhar_devagar_nao(self):
        self.assertFalse(self.chacoalhar(DetectorSacudida(), 10, 0.8))

    def test_tremidinha_nao_conta(self):
        self.assertFalse(self.chacoalhar(DetectorSacudida(amplitude=30), 30, 0.03, amplitude=10))

    def test_arrastar_reto_nao_conta(self):
        det = DetectorSacudida()
        self.assertFalse(any(det.adicionar(i * 0.02, i * 20, i * 5) for i in range(50)))

    def test_reiniciar(self):
        det = DetectorSacudida()
        self.chacoalhar(det, 5, 0.05)
        det.reiniciar()
        self.assertFalse(self.chacoalhar(det, 4, 0.05))


if __name__ == "__main__":
    unittest.main()
