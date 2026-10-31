import unittest

from pet import tela
from pet.tela import Area, Monitor

PRINCIPAL = Monitor("\\\\.\\DISPLAY1", 1, Area(0, 0, 1920, 1080), Area(0, 0, 1920, 1040), True)
ESQUERDA = Monitor("\\\\.\\DISPLAY2", 2, Area(-1280, 100, 0, 1124), Area(-1280, 100, 0, 1084), False)
LISTA = [PRINCIPAL, ESQUERDA]


class TestMonitores(unittest.TestCase):
    def test_rotulo(self):
        self.assertEqual(PRINCIPAL.rotulo, "Monitor 1 · 1920×1080 (principal)")
        self.assertEqual(ESQUERDA.rotulo, "Monitor 2 · 1280×1024")

    def test_por_nome(self):
        self.assertIs(tela.monitor_por_nome(LISTA, ESQUERDA.nome), ESQUERDA)

    def test_monitor_desligado_volta_pro_principal(self):
        self.assertIs(tela.monitor_por_nome(LISTA, "\\\\.\\DISPLAY9"), PRINCIPAL)

    def test_no_ponto(self):
        self.assertIs(tela.monitor_no_ponto(LISTA, 500, 500), PRINCIPAL)
        self.assertIs(tela.monitor_no_ponto(LISTA, -10, 500), ESQUERDA)

    def test_ponto_fora_de_todos_pega_o_mais_perto(self):
        # Acima do monitor da esquerda (ele começa em y=100)
        self.assertIs(tela.monitor_no_ponto(LISTA, -600, 20), ESQUERDA)
        self.assertIs(tela.monitor_no_ponto(LISTA, 3000, 500), PRINCIPAL)

    def test_monitores_de_verdade(self):
        lista = tela.monitores()
        self.assertGreaterEqual(len(lista), 1)
        self.assertTrue(lista[0].principal)
        for m in lista:
            self.assertLess(m.area.esquerda, m.area.direita)
            self.assertLessEqual(m.area.base, m.tela.base)


if __name__ == "__main__":
    unittest.main()
