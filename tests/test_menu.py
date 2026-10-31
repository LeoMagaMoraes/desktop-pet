"""Menu do clique direito (o novo, desenhado pelo próprio Clawd)."""

import unittest
from unittest import mock

from tests.test_mascote import BaseMascote


class TestMenu(BaseMascote):
    def test_abre_com_cabecalho_e_secoes(self):
        self.abrir_menu()
        self.assertTrue(self.m.menu.aberto)
        textos = self.textos_do_menu()
        for esperado in ("Clawd", "CUIDAR", "VER", "AJUSTES", "Alimentar", "Brincar", "Dormir",
                         "Status e tokens", "Clima", "Monitor", "Claude Code", "Modo Tamagotchi", "Sair"):
            self.assertIn(esperado, textos)
        self.assertTrue(any("XP" in t for t in textos))

    def test_menu_cabe_na_tela(self):
        self.abrir_menu()
        j, area = self.m.menu.janela, self.m.area
        self.assertGreaterEqual(j.winfo_rooty(), area.topo)
        self.assertLessEqual(j.winfo_rooty() + j.winfo_height(), area.base)
        self.assertGreaterEqual(j.winfo_rootx(), area.esquerda)
        self.assertLessEqual(j.winfo_rootx() + j.winfo_width(), area.direita)

    def test_item_executa_e_fecha(self):
        self.m.estado.status["fome"] = 40
        self.abrir_menu()
        self.clicar_no_menu("Alimentar")
        self.assertFalse(self.m.menu.aberto)
        self.esperar(lambda: self.m.acao == "comendo")
        self.assertEqual(self.m.acao, "comendo")

    def test_chave_liga_desliga_e_menu_continua_aberto(self):
        self.abrir_menu()
        self.clicar_no_menu("Modo Tamagotchi")
        self.assertFalse(self.m.estado.dados["modo_tamagotchi"])
        self.assertTrue(self.m.menu.aberto)
        self.assertTrue(any("status pausados" in t for t in self.textos_do_menu()))
        self.clicar_no_menu("Modo Tamagotchi")
        self.assertTrue(self.m.estado.dados["modo_tamagotchi"])

    def test_remedio_so_aparece_gripado(self):
        self.abrir_menu()
        self.assertNotIn("Dar remédio", self.textos_do_menu())
        self.m.menu.fechar()
        self.m.estado.dados["doente"] = True
        self.abrir_menu()
        self.assertIn("Dar remédio", self.textos_do_menu())

    def test_dormindo_vira_acordar(self):
        self.m.dormir()
        self.abrir_menu()
        textos = self.textos_do_menu()
        self.assertIn("Acordar", textos)
        self.assertNotIn("Dormir", textos)

    def test_pagina_claude_code_e_voltar(self):
        self.abrir_menu()
        self.clicar_no_menu("Claude Code")
        textos = self.textos_do_menu()
        self.assertIn("Contar só input e output", textos)
        self.assertIn("150.0M", textos)
        self.clicar_no_menu("Contar só input e output")
        self.assertTrue(self.m.cc.so_io)
        self.assertIn("1.5M", self.textos_do_menu())       # cada modo tem a sua meta
        self.clicar_no_menu("Sons")
        self.assertTrue(self.m.estado.dados["claude"]["sons"])
        self.m.menu._ir("principal")
        self.assertIn("CUIDAR", self.textos_do_menu())

    def test_esc_fecha(self):
        self.abrir_menu()
        self.m.menu.janela.event_generate("<Escape>")
        self.m.root.update()
        self.assertFalse(self.m.menu.aberto)

    def test_clicar_fora_fecha(self):
        self.abrir_menu()
        menu = self.m.menu
        menu._liberou_botao = True                  # o clique que abriu já foi solto
        with mock.patch("pet.menu.tela.botao_do_mouse_apertado", return_value=True), \
                mock.patch.object(menu.janela, "winfo_pointerxy", return_value=(-5000, -5000)):
            menu._vigiar_cliques()
        self.assertFalse(menu.aberto)

    def test_clicar_dentro_nao_fecha(self):
        self.abrir_menu()
        menu = self.m.menu
        menu._liberou_botao = True
        dentro = (menu.janela.winfo_rootx() + 5, menu.janela.winfo_rooty() + 5)
        with mock.patch("pet.menu.tela.botao_do_mouse_apertado", return_value=True), \
                mock.patch.object(menu.janela, "winfo_pointerxy", return_value=dentro):
            menu._vigiar_cliques()
        self.assertTrue(menu.aberto)

    def test_sair_pelo_menu(self):
        self.abrir_menu()
        self.clicar_no_menu("Sair")
        self.m.root.after(30)
        try:
            self.m.root.update()
        except Exception:
            pass
        with self.assertRaises(Exception):
            self.m.root.winfo_exists()


class TestMenuOvo(BaseMascote):
    SAVE = {"fase": "ovo", "xp": 40}

    def test_ovo_sem_barrinhas(self):
        self.abrir_menu()
        textos = self.textos_do_menu()
        self.assertIn("Ovo", textos)
        self.assertTrue(any("60 pra Filhote" in t for t in textos))


if __name__ == "__main__":
    unittest.main()
