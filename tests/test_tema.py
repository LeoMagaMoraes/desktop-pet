"""Modo escuro e modo claro da interface."""

import types
import unittest

from pet import menu, painel, tema
from tests.test_mascote import BaseMascote


class TestTema(unittest.TestCase):
    def test_temas_tem_as_mesmas_cores(self):
        self.assertEqual(set(tema.TEMAS["escuro"]), set(tema.TEMAS["claro"]))

    def test_nome_estranho_cai_no_padrao(self):
        self.assertEqual(tema.cores("roxo"), tema.TEMAS[tema.PADRAO])
        self.assertEqual(tema.cores(None), tema.TEMAS[tema.PADRAO])

    def test_aplicar_so_mexe_no_que_o_modulo_tem(self):
        modulo = types.SimpleNamespace(FUNDO="", TEXTO="")
        tema.aplicar("claro", modulo)
        self.assertEqual(modulo.FUNDO, tema.TEMAS["claro"]["FUNDO"])
        self.assertFalse(hasattr(modulo, "BORDA"))

    def test_modulos_de_interface_tem_todas_as_cores_que_usam(self):
        # Começam com o tema padrão já aplicado (nada fica vazio)
        for modulo, nomes in ((menu, ("FUNDO", "TEXTO", "PERIGO", "OK", "BOLINHA", "CAMPO")),
                              (painel, ("FUNDO_PAINEL", "VAZIO_PAINEL", "TEXTO", "AZUL"))):
            for nome in nomes:
                self.assertTrue(getattr(modulo, nome).startswith("#"), (modulo.__name__, nome))


class TestTemaNoPet(BaseMascote):
    def test_comeca_escuro(self):
        self.assertEqual(self.m.estado.dados["tema"], "escuro")
        self.assertEqual(menu.FUNDO, tema.TEMAS["escuro"]["FUNDO"])

    def test_chave_do_menu_troca_e_redesenha(self):
        m = self.m
        self.abrir_menu()
        self.assertIn("Modo escuro", self.textos_do_menu())
        self.clicar_no_menu("Modo escuro")
        self.assertEqual(m.estado.dados["tema"], "claro")
        self.assertTrue(m.menu.aberto)                       # continua aberto, já com as cores novas
        self.assertEqual(m.menu.corpo.cget("bg"), tema.TEMAS["claro"]["FUNDO"])
        self.assertIs(m.menu.icones, m.menu._icones["claro"])
        self.clicar_no_menu("Modo escuro")
        self.assertEqual(m.estado.dados["tema"], "escuro")
        self.assertEqual(m.menu.corpo.cget("bg"), tema.TEMAS["escuro"]["FUNDO"])

    def test_painel_aberto_troca_junto(self):
        m = self.m
        m.painel.abrir()
        m.alternar_tema()
        self.assertEqual(m.painel.canvas.cget("bg"), tema.TEMAS["claro"]["FUNDO_PAINEL"])
        m.painel.fechar()

    def test_janelinha_de_lembrete_usa_o_tema(self):
        m = self.m
        m.alternar_tema()
        m.dialogo_lembrete.abrir()
        self.assertEqual(m.dialogo_lembrete.janela.cget("bg"), tema.TEMAS["claro"]["FUNDO"])
        self.assertEqual(m.dialogo_lembrete.texto.cget("bg"), tema.TEMAS["claro"]["CAMPO"])
        m.dialogo_lembrete.fechar()

    def test_tema_fica_salvo(self):
        m = self.m
        m.alternar_tema()
        self.assertEqual(m.estado.carregar(m.estado.caminho).dados["tema"], "claro")


class TestAbreNoClaro(BaseMascote):
    SAVE = {"fase": "clawd", "xp": 1000, "tema": "claro"}

    def test_abre_com_o_tema_salvo(self):
        self.assertEqual(menu.FUNDO, tema.TEMAS["claro"]["FUNDO"])
        self.assertEqual(painel.FUNDO_PAINEL, tema.TEMAS["claro"]["FUNDO_PAINEL"])
        self.abrir_menu()
        self.assertEqual(self.m.menu.corpo.cget("bg"), tema.TEMAS["claro"]["FUNDO"])


if __name__ == "__main__":
    unittest.main()
