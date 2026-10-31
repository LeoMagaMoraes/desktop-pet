"""Pinguim, patinho de borracha, fênix e corujinha: desenho e o jeito de cada um."""

import time
import unittest

from pet import clima, especies, pixelart as p
from tests.test_clima import tempo
from tests.test_mascote import BaseMascote

NOVOS = ("pinguim", "pato", "fenix", "coruja")


class TestDesenhos(unittest.TestCase):
    def test_todo_bicho_tem_todas_as_animacoes_e_pisa_no_chao(self):
        for bicho in especies.ESPECIES:
            for fase in p.FASES:
                an = p.animacoes(fase, especie=bicho)
                self.assertEqual(set(an), set(p.animacoes(fase)), f"{bicho}/{fase}")
                for nome, (ms, quadros) in an.items():
                    for g in quadros:
                        self.assertEqual((g.largura, g.altura), (p.LARGURA, p.ALTURA), f"{bicho}/{fase}/{nome}")
                if fase != "ovo":
                    for g in an["parado"][1] + an["andando"][1]:
                        self.assertTrue(any(g.px[-1]), f"{bicho}/{fase}")

    def test_cores_de_cada_um(self):
        esperado = {"pinguim": {p.PINGUIM, p.BRANCO_PINGUIM, p.LARANJA_BICO},
                    "pato": {p.PATO, p.BICO_PATO},
                    "fenix": {p.FENIX, p.CHAMA, p.CHAMA_CLARA},
                    "coruja": {p.CORUJA, p.DISCO, p.BICO_CORUJA}}
        for bicho, cores in esperado.items():
            g = p.animacoes("clawd", especie=bicho)["parado"][1][0]
            usadas = {c for linha in g.px for c in linha if c}
            self.assertTrue(cores <= usadas, bicho)
            self.assertNotIn(p.LARANJA, usadas - {p.LARANJA_BICO}, bicho)

    def test_aves_tem_pe_de_outra_cor(self):
        for bicho in ("pinguim", "pato", "fenix", "coruja"):
            g = p.animacoes("clawd", especie=bicho)["parado"][1][0]
            pe = {c for c in g.px[-1] if c}
            pele = p.BICHOS[bicho]["estilo"]["pele"]
            self.assertEqual(pe, {pele.pernas}, bicho)

    def test_icones_nao_mudaram_as_cores_dos_outros(self):
        # Letras repetidas na paleta já deixaram a nuvem marrom uma vez
        self.assertEqual({c for l in p.ICONES["nuvem"].px for c in l if c}, {"#D8DEE6"})
        for bicho in NOVOS:
            self.assertGreater(p.ICONES[especies.especie(bicho).icone].pixels_pintados(), 20)


class TestPersonalidade(unittest.TestCase):
    def test_pinguim_gosta_de_frio(self):
        frio = tempo(73, temperatura=-3)                  # nevando
        self.assertEqual(especies.ajustar_roupas("pinguim", clima.roupas(frio), frio), frozenset())
        e = especies.ajustar_efeitos("pinguim", clima.efeitos_nos_status(frio), frio)
        self.assertEqual(e["mult_fome"], 1.0)
        self.assertGreater(e["bonus_felicidade"], 0)
        quente = tempo(3, temperatura=28)
        self.assertGreater(especies.ajustar_efeitos("pinguim", clima.efeitos_nos_status(quente), quente)
                           ["mult_energia"], 1)
        # Os outros continuam sentindo frio
        self.assertIn("cachecol", especies.ajustar_roupas("clawd", clima.roupas(frio), frio))

    def test_coruja_dorme_de_dia(self):
        dia, noite = tempo(0), tempo(0, dia=False)
        self.assertEqual(especies.ajustar_roupas("coruja", clima.roupas(dia), dia), {"pijama"})
        self.assertNotIn("pijama", especies.ajustar_roupas("coruja", clima.roupas(noite), noite))
        e_dia = especies.ajustar_efeitos("coruja", clima.efeitos_nos_status(dia), dia)
        e_noite = especies.ajustar_efeitos("coruja", clima.efeitos_nos_status(noite), noite)
        self.assertTrue(e_dia["dorminhoco"])
        self.assertGreater(e_dia["mult_energia"], e_noite["mult_energia"])

    def test_apresentacao_com_artigo(self):
        self.assertEqual(especies.especie("fenix").apresentacao, "a Fênix")
        self.assertEqual(especies.especie("coruja").apresentacao, "a Corujinha")
        self.assertEqual(especies.especie("pato").apresentacao, "o Patinho de borracha")


class TestNaTela(BaseMascote):
    SAVE = {"fase": "clawd", "xp": 2000}

    def trocar(self, bicho, fase="clawd", xp=1500):
        m = self.m
        m.trocar_pet(bicho)
        m.estado.dados.update(fase=fase, xp=xp)
        m.fase = fase
        m.sprites = m._biblioteca(fase)
        m.mudar("parado", 30)
        return m

    def test_pato_pede_pra_explicar_o_bug(self):
        self.trocar("pato")
        self.hook(evento="erro", comando="python x.py", codigo=1)
        self.assertIn("Linha por linha", self.m.balao.texto)
        self.m.cc._ultimo_erro = 0
        self.hook(evento="teste", passou=False)
        self.assertIn("Me conta o que ele faz", self.m.balao.texto)

    def test_pato_faz_quack(self):
        from unittest import mock
        m = self.trocar("pato")
        m.estado.dados["claude"]["sons"] = True
        with mock.patch("pet.mascote.sons.tocar") as tocar, mock.patch("pet.mascote.random.random", return_value=0):
            self.clicar()
        tocar.assert_called_once_with("quack")
        self.assertIn("Quack", m.balao.texto)

    def test_fenix_renasce_das_cinzas_sem_perder_xp(self):
        m = self.trocar("fenix", "filhote", 400)
        m.estado.status["felicidade"] = 0
        m.tama._prox_checagem = 0
        m.tama.tick()
        self.assertEqual(m.fase, "ovo")
        self.assertEqual(m.estado.status["felicidade"], 100)
        self.assertEqual(m.estado.dados["xp"], 400)
        self.assertIn("cinzas", m.balao.texto)
        m.verificar_evolucao()
        self.assertEqual(m.acao, "parado")          # espera as cinzas antes de chocar
        m._renasceu_em -= 5
        m.verificar_evolucao()
        self.assertEqual(m.acao, "chocando")
        self.rodar_ticks(3.3)
        self.assertEqual(m.fase, "filhote")
        self.assertIn("Renasci das cinzas", m.balao.texto)

    def test_fenix_renasce_mesmo_com_sol(self):
        # O bônus do sol devolve um tiquinho de felicidade antes da checagem
        from datetime import datetime
        from unittest import mock
        from tests.test_clima import EXEMPLO
        m = self.trocar("fenix", "filhote", 400)
        m.clima.atual = clima.ler_previsao(EXEMPLO)            # céu limpo, de dia
        m.estado.status["felicidade"] = 0
        m.tama._ultimo -= 60
        m.tama._prox_checagem = 0
        with mock.patch.object(m.clima, "agora_na_cidade", return_value=datetime(2026, 10, 31, 11, 30)):
            m.tama.tick()
        self.assertEqual(m.fase, "ovo")

    def test_outros_bichos_nao_renascem(self):
        m = self.trocar("coruja")
        m.estado.status["felicidade"] = 0
        m.tama._prox_checagem = 0
        m.tama.tick()
        self.assertEqual(m.fase, "clawd")

    def test_espirros_de_cada_um(self):
        for bicho, efeito, emoji in (("pinguim", "floco", "❄"), ("coruja", "pena", "🪶")):
            m = self.trocar(bicho)
            m.espirrar()
            self.assertIn(emoji, m.balao.texto)
            self.esperar(lambda: any(m.canvas.itemcget(pt.item, "image") == str(m.imagens_efeito[efeito])
                                     for pt in m.efeitos.particulas))

    def test_pinguim_sente_calor_antes(self):
        from unittest import mock
        from datetime import datetime
        import copy, json
        from tests.test_clima import EXEMPLO
        m = self.trocar("pinguim")
        d = copy.deepcopy(EXEMPLO)
        d["current"].update(temperature_2m=27)
        m.clima.atual = clima.ler_previsao(d)
        with mock.patch.object(m.clima, "agora_na_cidade", return_value=datetime(2026, 10, 31, 11, 30)):
            m.clima._vestir()
            self.assertIsNotNone(m.efeitos.ventilador)      # 27 °C já é calor pro pinguim
            m.trocar_pet("clawd")
            m.clima._vestir()
            self.assertIsNone(m.efeitos.ventilador)         # pro Clawd ainda não

    def test_menu_lista_os_sete(self):
        self.abrir_menu()
        self.clicar_no_menu("Trocar de pet")
        textos = self.textos_do_menu()
        for esp in especies.ESPECIES.values():
            self.assertIn(f"{esp.nome} {esp.emoji}", textos)


if __name__ == "__main__":
    unittest.main()
