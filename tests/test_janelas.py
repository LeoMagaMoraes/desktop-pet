"""Andar em cima das janelas: a lógica das plataformas e o pet de verdade com janelas de mentira."""

import time
import unittest
from unittest import mock

from pet import fisica
from pet.janelas import Plataformas, velocidade_do_pulo
from pet.tela import Area, JanelaAberta
from tests.test_mascote import BaseMascote

AREA = Area(0, 0, 1920, 1040)
ALTURA = 60


def janela(hwnd, esq, topo, dir_, base):
    return JanelaAberta(hwnd, esq, topo, dir_, base, f"janela {hwnd}")


class TestPlataformas(unittest.TestCase):
    def test_sem_janela_o_chao_e_a_barra(self):
        self.assertEqual(Plataformas().chao_abaixo(500, 100, AREA, ALTURA), (1040, None))

    def test_pousa_na_janela_mais_alta_embaixo_dos_pes(self):
        p = Plataformas([janela(1, 100, 600, 900, 900), janela(2, 300, 400, 700, 800)])
        self.assertEqual(p.chao_abaixo(500, 100, AREA, ALTURA), (400, 2))
        self.assertEqual(p.chao_abaixo(800, 100, AREA, ALTURA), (600, 1))   # fora da 2, cai na 1
        self.assertEqual(p.chao_abaixo(50, 100, AREA, ALTURA), (1040, None))

    def test_janela_acima_dos_pes_nao_conta(self):
        p = Plataformas([janela(1, 100, 300, 900, 900)])
        self.assertEqual(p.chao_abaixo(500, 500, AREA, ALTURA), (1040, None))
        self.assertEqual(p.chao_abaixo(500, 300, AREA, ALTURA), (300, 1))    # em pé em cima dela

    def test_borda_tapada_por_janela_da_frente_nao_da_pra_pisar(self):
        # A janela 2 está na frente e cobre o meio da borda da janela 1
        p = Plataformas([janela(2, 400, 200, 600, 700), janela(1, 100, 500, 900, 900)])
        self.assertIsNone(p.superficie(1, 500, AREA, ALTURA))
        self.assertEqual(p.superficie(1, 200, AREA, ALTURA), 500)
        self.assertEqual(p.chao_abaixo(500, 100, AREA, ALTURA), (200, 2))

    def test_janela_colada_no_topo_nao_tem_espaco(self):
        maximizada = Plataformas([janela(1, 0, 0, 1920, 1040)])
        self.assertEqual(maximizada.chao_abaixo(500, -50, AREA, ALTURA), (1040, None))

    def test_destinos_respeitam_o_alcance(self):
        p = Plataformas([janela(1, 100, 600, 900, 900), janela(2, 1000, 100, 1800, 500)])
        destinos = p.destinos(500, 1040, AREA, ALTURA, meia=40, alcance=600)
        self.assertEqual([d[2] for d in destinos], [1])                     # a 2 é alta demais
        x, topo, _ = destinos[0]
        self.assertTrue(100 + 40 <= x <= 900 - 40)
        # Em cima da janela 1, a 2 fica a 500 px: dá pra pular nela, e a própria 1 não conta
        de_cima = [d[2] for d in p.destinos(500, 600, AREA, ALTURA, 40, 600, atual=1)]
        self.assertEqual(de_cima, [2])

    def test_pulo_cai_no_alvo(self):
        g = 2600
        for (x, y, ax, ay) in ((500, 1040, 900, 600), (900, 600, 300, 1040), (100, 800, 150, 300)):
            vx, vy = velocidade_do_pulo(x, y, ax, ay, g, 40)
            # Voo livre (sem chão) até cruzar a altura do alvo descendo
            corpo = fisica.Corpo(x, y, vx, vy)
            lim = fisica.Limites(-10000, 10000, -10000, 10000, 1, 1)
            for _ in range(5000):
                antes = corpo.y
                fisica.passo(corpo, lim, fisica.Parametros(gravidade=g), 1 / 480)
                if corpo.vy > 0 and antes < ay <= corpo.y:
                    break
            self.assertAlmostEqual(corpo.x, ax, delta=10)
            self.assertAlmostEqual(corpo.y, ay, delta=10)


class TestPetNasJanelas(BaseMascote):
    def soltar_de(self, x, y):
        m = self.m
        m.corpo.x, m.corpo.y = x, y
        m.corpo.vx = m.corpo.vy = 0.0
        m.corpo.no_chao = False
        m.janelas.soltar()
        m.mudar("caindo")
        self.rodar_ticks(1.5)

    def janela_no_meio(self, hwnd=7, topo_acima_da_barra=400, largura=700):
        a = self.m.area
        cx = (a.esquerda + a.direita) // 2
        return janela(hwnd, cx - largura // 2, a.base - topo_acima_da_barra, cx + largura // 2, a.base - 100)

    def test_pousa_em_cima_da_janela(self):
        m = self.m
        j = self.janela_no_meio()
        self.janelas([j])
        self.soltar_de((j.esquerda + j.direita) / 2, j.topo - 200)
        self.assertNotEqual(m.acao, "caindo")
        self.assertEqual(m.corpo.y, j.topo)
        self.assertEqual(m.janelas.hwnd, j.hwnd)
        self.assertEqual(m.estado.dados["lugar_favorito"]["y"], j.topo)

    def test_fora_da_janela_cai_na_barra(self):
        m = self.m
        j = self.janela_no_meio()
        self.janelas([j])
        self.soltar_de(j.esquerda - 120, j.topo - 200)
        self.assertEqual(m.corpo.y, m.area.base)
        self.assertIsNone(m.janelas.hwnd)

    def test_carona_quando_a_janela_mexe(self):
        m = self.m
        j = self.janela_no_meio()
        self.janelas([j])
        self.soltar_de((j.esquerda + j.direita) / 2, j.topo - 50)
        x0 = m.corpo.x
        movida = janela(j.hwnd, j.esquerda + 80, j.topo - 50, j.direita + 80, j.base - 50)
        m.janelas.plataformas.atualizar([movida])
        m.mudar("parado", 10)
        m.janelas.tick()
        self.assertAlmostEqual(m.corpo.x, x0 + 80)
        self.assertEqual(m.corpo.y, movida.topo)

    def test_janela_fechou_ele_cai(self):
        m = self.m
        j = self.janela_no_meio()
        self.janelas([j])
        self.soltar_de((j.esquerda + j.direita) / 2, j.topo - 50)
        m.janelas.plataformas.atualizar([])
        m.mudar("parado", 10)
        m.janelas.tick()
        self.assertEqual(m.acao, "caindo")
        self.rodar_ticks(1.5)
        self.assertEqual(m.corpo.y, m.area.base)

    def test_outra_janela_tapou_ele_cai(self):
        m = self.m
        j = self.janela_no_meio()
        self.janelas([j])
        self.soltar_de((j.esquerda + j.direita) / 2, j.topo - 50)
        frente = janela(99, j.esquerda, j.topo - 300, j.direita, j.base)
        m.janelas.plataformas.atualizar([frente, j])
        m.mudar("parado", 10)
        m.janelas.tick()
        self.assertEqual(m.acao, "caindo")

    def test_beirada_vira_ou_pula(self):
        m = self.m
        j = self.janela_no_meio()
        self.janelas([j])
        # Quase na beirada: o próximo passo já passa da borda da direita
        self.soltar_de(j.direita - m.sprites.meia_largura * 0.5 - 1, j.topo - 50)
        m.direcao = 1
        m.mudar("andando", 10)
        with mock.patch("pet.janelas.random.random", return_value=0.99):   # vira
            m._andar(0.1)
        self.assertEqual(m.direcao, -1)
        self.assertEqual(m.acao, "andando")
        m.direcao = 1
        with mock.patch("pet.janelas.random.random", return_value=0.0):    # pula
            m._andar(0.1)
        self.assertEqual(m.acao, "caindo")
        self.rodar_ticks(1.5)
        self.assertEqual(m.corpo.y, m.area.base)

    def test_pula_sozinho_pra_cima_de_uma_janela(self):
        m = self.m
        j = self.janela_no_meio(topo_acima_da_barra=300)
        self.janelas([j])
        m.corpo.x = j.esquerda - 150
        m.mudar("parado", 10)
        with mock.patch("pet.janelas.random.random", return_value=0.0):
            self.assertTrue(m.janelas.tentar_pular())
        self.assertEqual(m.acao, "caindo")
        self.assertLess(m.corpo.vy, 0)
        self.rodar_ticks(2.5)
        self.assertEqual(m.corpo.y, j.topo)
        self.assertEqual(m.janelas.hwnd, j.hwnd)

    def test_pulo_longe_pra_beirada_nao_escorrega_pra_fora(self):
        # Alvo no cantinho da janela: chega rápido de lado e tem que fincar o pé
        m = self.m
        j = self.janela_no_meio(topo_acima_da_barra=300)
        self.janelas([j])
        m.corpo.x = j.esquerda - 150
        m.mudar("parado", 10)
        with mock.patch("pet.janelas.random.random", return_value=0.0), \
                mock.patch("pet.janelas.random.uniform", side_effect=lambda a, b: b):
            self.assertTrue(m.janelas.tentar_pular())
        self.rodar_ticks(2.5)
        self.assertEqual(m.corpo.y, j.topo)
        self.assertEqual(m.janelas.hwnd, j.hwnd)

    def test_escorregar_pra_fora_da_janela_faz_cair(self):
        m = self.m
        j = self.janela_no_meio()
        self.janelas([j])
        # Chega deslizando rápido perto da beirada direita
        m.corpo.x, m.corpo.y = j.direita - 30, j.topo
        m.corpo.vx, m.corpo.vy = 900, 0.0
        m.corpo.no_chao = True
        m.mudar("caindo")
        self.rodar_ticks(1.5)
        self.assertEqual(m.corpo.y, m.area.base)            # não fica flutuando no ar

    def test_desligar_pelo_menu_derruba(self):
        m = self.m
        j = self.janela_no_meio()
        self.janelas([j])
        self.soltar_de((j.esquerda + j.direita) / 2, j.topo - 50)
        self.abrir_menu()
        self.assertIn("Andar nas janelas", self.textos_do_menu())
        m.janelas.atualizar = lambda forcar=False: m.janelas.plataformas.atualizar(
            [j] if m.janelas.ligado else [])
        self.clicar_no_menu("Andar nas janelas")
        self.assertFalse(m.estado.dados["andar_nas_janelas"])
        self.assertEqual(m.acao, "caindo")
        self.rodar_ticks(1.5)
        self.assertEqual(m.corpo.y, m.area.base)

    def test_area_nova_nao_tira_ele_da_janela(self):
        m = self.m
        j = self.janela_no_meio()
        self.janelas([j])
        self.soltar_de((j.esquerda + j.direita) / 2, j.topo - 50)
        m._reler_area()
        self.assertEqual(m.corpo.y, j.topo)


if __name__ == "__main__":
    unittest.main()
