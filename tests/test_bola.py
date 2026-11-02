"""Brincar de bola e o renascer da Fênix anciã."""

import time
import unittest
from unittest import mock

from pet import bola, pixelart
from pet.tela import JanelaAberta
from tests.test_mascote import BaseMascote


class TestArteDaBola(unittest.TestCase):
    def test_girar_quatro_vezes_volta_ao_comeco(self):
        g = pixelart.BOLA
        girada = bola._girar(g)
        self.assertNotEqual(girada.px, g.px)
        for _ in range(3):
            girada = bola._girar(girada)
        self.assertEqual(girada.px, g.px)

    def test_animacoes_de_jogo(self):
        for bicho in pixelart.BICHOS:
            an = pixelart.animacoes("clawd", especie=bicho)
            self.assertIn("correndo", an)
            chute = an["chutando"][1][0]
            self.assertNotEqual(chute.px, an["parado"][1][0].px, bicho)


class TestBrincarDeBola(BaseMascote):
    def bola(self):
        return self.m.brincadeira.bola

    def test_brincar_solta_uma_bola_e_ele_chuta(self):
        m = self.m
        m.brincar()
        self.assertTrue(m.brincadeira.ativa)
        b = self.bola()
        self.assertLess(b.corpo.y, m.corpo.y)                 # cai do alto
        self.rodar_ticks(5)
        self.assertGreaterEqual(m.brincadeira.chutes, 1)
        self.assertTrue(b.janela.winfo_exists())

    def test_bola_tem_a_fisica_do_pet(self):
        m = self.m
        m.brincar()
        b = self.bola()
        m.brincadeira.meta = 99                                 # não acaba no meio do teste
        # Chutão pra direita: bate na borda, volta e assenta no chão
        b.corpo.x = m.area.direita - 100
        b.corpo.y = m.area.base - 50
        b.chutar(3000 * m.k, -500 * m.k)
        bateu = False
        for _ in range(150):
            b.tick(1 / 30)
            bateu = bateu or b.corpo.vx < 0
            self.assertLessEqual(b.corpo.x + b.meia, m.area.direita + 1)
        self.assertTrue(bateu)
        self.assertEqual(b.corpo.y, m.area.base)
        self.assertTrue(b.parada)

    def test_bola_pousa_em_cima_de_janela(self):
        m = self.m
        a = m.area
        j = JanelaAberta(7, a.esquerda + 200, a.base - 400, a.esquerda + 900, a.base - 100, "janela")
        self.janelas([j])
        m.brincar()
        b = self.bola()
        m.brincadeira.meta = 99
        b.corpo.x, b.corpo.y = a.esquerda + 500, j.topo - 200
        b.chutar(0, 0)
        for _ in range(90):
            b.tick(1 / 30)
        self.assertEqual(b.corpo.y, j.topo)

    def test_pegar_e_arremessar_a_bola(self):
        m = self.m
        m.brincar()
        b = self.bola()
        m.root.update()
        x, y = b.corpo.x, b.corpo.y - b.meia
        c = b.canvas

        def ev(tipo, px, py, **kw):
            c.event_generate(tipo, x=int(px - c.winfo_rootx()), y=int(py - c.winfo_rooty()),
                             rootx=int(px), rooty=int(py), **kw)
        ev("<ButtonPress-1>", x, y)
        for i in range(1, 8):
            ev("<B1-Motion>", x + i * 30, y - i * 30, state=0x100)
            time.sleep(0.01)
        self.assertTrue(b.arrastando)
        ev("<ButtonRelease-1>", x + 240, y - 240)
        self.assertFalse(b.arrastando)
        self.assertGreater(b.corpo.vx, 0)
        self.assertLess(b.corpo.vy, 0)

    def test_jogo_acaba_depois_dos_chutes(self):
        m = self.m
        m.brincar()
        b = self.bola()
        b.corpo.y, b.corpo.vx, b.corpo.vy, b.corpo.no_chao = m.area.base, 0.0, 0.0, True
        m.brincadeira.chutes = m.brincadeira.meta
        m.mudar("parado")
        m.brincadeira.tick(1 / 30)
        self.assertFalse(m.brincadeira.ativa)
        self.assertFalse(b.janela.winfo_exists())
        self.assertEqual(m.acao, "comemorando")
        self.assertIn("Que jogo bom", m.balao.texto)

    def test_lembrete_interrompe_o_jogo(self):
        m = self.m
        m.brincar()
        m.lembretes.ativo = {"id": "x", "texto": "Reunião"}
        m.brincadeira.tick(1 / 30)
        self.assertFalse(m.brincadeira.ativa)

    def test_em_cima_da_janela_pula_pra_baixo_atras_da_bola(self):
        m = self.m
        a = m.area
        j = JanelaAberta(7, a.esquerda + 200, a.base - 300, a.esquerda + 900, a.base - 100, "janela")
        self.janelas([j])
        m.corpo.x, m.corpo.y = a.esquerda + 500, j.topo
        m.janelas.pousou(m.corpo.x, m.corpo.y)
        self.assertEqual(m.janelas.hwnd, 7)
        m.brincar()
        b = self.bola()
        b.corpo.x, b.corpo.y, b.corpo.vx, b.corpo.vy, b.corpo.no_chao = a.esquerda + 1200, a.base, 0, 0, True
        m.mudar("parado")
        m.brincadeira.tick(1 / 30)
        self.assertEqual(m.acao, "caindo")
        self.rodar_ticks(1.5)
        self.assertEqual(m.corpo.y, a.base)

    def test_corre_mais_rapido_que_anda(self):
        m = self.m
        x = m.corpo.x
        m.direcao = 1
        m.mudar("correndo")
        m._atualizar(time.perf_counter(), 0.1)
        correu = m.corpo.x - x
        m.corpo.x = x
        m.mudar("andando", 5)
        m._atualizar(time.perf_counter(), 0.1)
        self.assertGreater(correu, 3 * (m.corpo.x - x))

    def test_sair_fecha_a_bola(self):
        self.m.brincar()
        b = self.bola()
        self.m.brincadeira.parar(falar=False)
        self.assertFalse(b.janela.winfo_exists())


class TestBrincarOvo(BaseMascote):
    SAVE = {"fase": "ovo", "xp": 10}

    def test_ovo_so_rola(self):
        self.m.brincar()
        self.assertFalse(self.m.brincadeira.ativa)
        self.assertIn("Rolei", self.m.balao.texto)


class TestFenixAncia(BaseMascote):
    SAVE = {"especie": "fenix", "fase": "anciao", "xp": 12000, "xp_gasto": 300}

    def test_menu_mostra_renascer(self):
        self.assertTrue(self.m.pode_renascer())
        self.abrir_menu()
        self.assertIn("Renascer", self.textos_do_menu())

    def test_renascer_volta_como_ovo_e_conta(self):
        m = self.m
        with mock.patch("pet.mascote.messagebox.askyesno", return_value=True):
            m.renascer_de_vontade()
        d = m.estado.dados
        self.assertEqual(m.fase, "ovo")
        self.assertEqual((d["xp"], d["xp_gasto"], d["renascimentos"]), (0, 0, 1))
        self.assertIn("Renascimento nº 1", m.balao.texto)
        self.assertFalse(m.pode_renascer())
        # Continua ovo: o XP zerou, então ele não volta direto pra anciã
        m._renasceu_em -= 5
        m.mudar("parado", 5)
        m.verificar_evolucao()
        self.assertEqual(m.fase, "ovo")

    def test_desistir_nao_muda_nada(self):
        m = self.m
        with mock.patch("pet.mascote.messagebox.askyesno", return_value=False):
            m.renascer_de_vontade()
        self.assertEqual((m.fase, m.estado.dados["xp"]), ("anciao", 12000))

    def test_renascimentos_sao_da_fenix(self):
        m = self.m
        with mock.patch("pet.mascote.messagebox.askyesno", return_value=True):
            m.renascer_de_vontade()
        m.trocar_pet("clawd")
        self.assertEqual(m.estado.dados["renascimentos"], 0)
        m.trocar_pet("fenix")
        self.assertEqual(m.estado.dados["renascimentos"], 1)


class TestOutrosAnciaosNaoRenascem(BaseMascote):
    SAVE = {"fase": "anciao", "xp": 12000}

    def test_clawd_anciao_sem_renascer(self):
        self.assertFalse(self.m.pode_renascer())
        self.abrir_menu()
        self.assertNotIn("Renascer", self.textos_do_menu())


if __name__ == "__main__":
    unittest.main()
