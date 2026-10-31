"""Clima: regras puras (com uma resposta real do Open-Meteo) e o Clawd reagindo ao tempo."""

import copy
import json
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from pet import clima, necessidades
from pet.clima import Clima
from pet.clima_controle import ler_cidade
from pet.estado import PADRAO
from tests.test_mascote import BaseMascote

EXEMPLO = json.loads((Path(__file__).parent / "dados" / "openmeteo_floripa.json").read_text(encoding="utf-8"))
GEOCODING = {"results": [
    {"name": "Florianópolis", "admin1": "Acre", "latitude": -7.9, "longitude": -73.2, "population": None},
    {"name": "Florianópolis", "admin1": "Santa Catarina", "latitude": -27.59667, "longitude": -48.54917,
     "population": 508826},
]}


def com_tempo(codigo=1, temperatura=22.8, dia=True):
    """Cópia da resposta real trocando o tempo atual."""
    d = copy.deepcopy(EXEMPLO)
    d["current"].update(weather_code=codigo, temperature_2m=temperatura, is_day=int(dia))
    return d


def tempo(codigo=1, temperatura=22.8, dia=True):
    return clima.ler_previsao(com_tempo(codigo, temperatura, dia))


class TestLeitura(unittest.TestCase):
    def test_resposta_real(self):
        c = clima.ler_previsao(EXEMPLO)
        self.assertEqual((c.temperatura, c.codigo, c.eh_dia), (22.8, 1, True))
        self.assertEqual((c.categoria, c.descricao), ("limpo", "poucas nuvens"))
        self.assertEqual(c.hora_local, datetime(2026, 10, 31, 11, 15))
        self.assertEqual(len(c.chuva_por_hora), 24)

    def test_categorias(self):
        casos = {0: "limpo", 3: "nublado", 45: "neblina", 53: "garoa", 63: "chuva", 81: "chuva",
                 73: "neve", 95: "tempestade", 12345: "nublado"}
        for codigo, categoria in casos.items():
            self.assertEqual(tempo(codigo).categoria, categoria, codigo)

    def test_emoji_de_noite(self):
        self.assertEqual(tempo(0, dia=False).emoji, "🌙")
        self.assertEqual(tempo(0).emoji, "☀")

    def test_salvar_e_ler(self):
        c = clima.ler_previsao(EXEMPLO)
        de_volta = Clima.do_save(json.loads(json.dumps(c.para_save())))
        self.assertEqual(de_volta, c)


class TestCidade(unittest.TestCase):
    def test_escolhe_o_estado_certo(self):
        achada = clima.procurar_cidade("Florianópolis", "Santa Catarina", baixar=lambda url, p: GEOCODING)
        self.assertEqual(achada, ("Florianópolis", "Santa Catarina", -27.59667, -48.54917))

    def test_sem_estado_pega_a_mais_populosa(self):
        achada = clima.procurar_cidade("Florianópolis", baixar=lambda url, p: GEOCODING)
        self.assertEqual(achada[1], "Santa Catarina")

    def test_nao_achou(self):
        self.assertIsNone(clima.procurar_cidade("Xyzzy", baixar=lambda url, p: {}))

    def test_ler_cidade(self):
        self.assertEqual(ler_cidade("Florianópolis, SC"), ("Florianópolis", "Santa Catarina"))
        self.assertEqual(ler_cidade("Recife - PE"), ("Recife", "Pernambuco"))
        self.assertEqual(ler_cidade("Curitiba"), ("Curitiba", None))
        self.assertEqual(ler_cidade("  "), (None, None))


class TestRoupas(unittest.TestCase):
    def test_sol_de_dia(self):
        self.assertEqual(clima.roupas(tempo(0)), {"oculos_sol"})

    def test_nublado_normal(self):
        self.assertEqual(clima.roupas(tempo(3)), set())

    def test_chuva_e_garoa(self):
        self.assertEqual(clima.roupas(tempo(63)), {"guarda_chuva", "galochas"})
        self.assertEqual(clima.roupas(tempo(51)), {"guarda_chuva", "galochas"})

    def test_neve(self):
        self.assertEqual(clima.roupas(tempo(73, temperatura=-2)), {"gorro", "cachecol"})

    def test_frio_qualquer_tempo(self):
        self.assertIn("cachecol", clima.roupas(tempo(3, temperatura=12)))

    def test_noite_pijama(self):
        roupas = clima.roupas(tempo(0, dia=False))
        self.assertIn("pijama", roupas)
        self.assertNotIn("oculos_sol", roupas)

    def test_sem_clima(self):
        self.assertEqual(clima.roupas(None), frozenset())


class TestEfeitos(unittest.TestCase):
    def test_sol_alegra(self):
        self.assertGreater(clima.efeitos_nos_status(tempo(0))["bonus_felicidade"], 0)

    def test_chuva_da_preguica(self):
        e = clima.efeitos_nos_status(tempo(63))
        self.assertGreater(e["mult_energia"], 1)
        self.assertTrue(e["dorminhoco"])

    def test_frio_da_fome(self):
        self.assertGreater(clima.efeitos_nos_status(tempo(3, temperatura=10))["mult_fome"], 1)

    def test_passar_tempo_com_efeitos(self):
        base = copy.deepcopy(PADRAO)
        sol, frio = copy.deepcopy(base), copy.deepcopy(base)
        necessidades.passar_tempo(base, 1)
        necessidades.passar_tempo(sol, 1, bonus_felicidade=4)
        necessidades.passar_tempo(frio, 1, mult_fome=1.5)
        self.assertGreater(sol["status"]["felicidade"], base["status"]["felicidade"])
        self.assertGreater(sol["status"]["felicidade"], PADRAO["status"]["felicidade"])   # subiu
        self.assertLess(frio["status"]["fome"], base["status"]["fome"])


class TestPrevisao(unittest.TestCase):
    def test_proxima_chuva_na_resposta_real(self):
        c = clima.ler_previsao(EXEMPLO)
        self.assertEqual(clima.proxima_chuva(c, datetime(2026, 10, 31, 9, 0)),
                         (datetime(2026, 10, 31, 14, 0), 59))
        self.assertIsNone(clima.proxima_chuva(c, datetime(2026, 10, 31, 16, 0)))

    def test_resumo(self):
        texto = clima.resumo(clima.ler_previsao(EXEMPLO), "Florianópolis", datetime(2026, 10, 31, 11, 15))
        self.assertIn("Florianópolis: 23°C, poucas nuvens", texto)
        self.assertIn("Chuva mais tarde: até 69% lá pelas 15h", texto)


class TestClawdNoClima(BaseMascote):
    def preparar(self, resposta=None, falhar=False):
        """Troca a internet por respostas prontas e roda uma busca."""
        def baixar(url, params):
            if falhar:
                raise OSError("sem internet")
            return GEOCODING if "geocoding" in url else (resposta or EXEMPLO)
        cl = self.m.clima
        cl.baixar = baixar
        cl._buscar()
        cl._prox_checagem = 0
        # "Você está longe do PC": senão o aviso da manhã depende de você mexer no mouse durante o teste
        with mock.patch("pet.clima_controle.tela.segundos_ocioso", return_value=9999):
            cl.tick()
        self.m.root.update()

    def test_busca_cidade_uma_vez_e_salva(self):
        self.preparar()
        d = self.m.clima.d
        self.assertEqual((d["lat"], d["lon"], d["estado"]), (-27.59667, -48.54917, "Santa Catarina"))
        self.assertEqual(self.m.clima.atual.temperatura, 22.8)
        self.assertIsNotNone(d["atual"])

    def test_sol_veste_oculos(self):
        self.preparar(com_tempo(0))
        with mock.patch.object(self.m.clima, "agora_na_cidade", return_value=datetime(2026, 10, 31, 11, 30)):
            self.m.clima._vestir()
        self.assertIn("oculos_sol", self.m.roupas)

    def test_chuva_veste_guarda_chuva_sem_gotas_na_tela(self):
        m = self.m
        janelas_antes = len(m.root.winfo_children())
        with mock.patch.object(m.clima, "agora_na_cidade", return_value=datetime(2026, 10, 31, 11, 30)):
            self.preparar(com_tempo(63))
        self.assertTrue({"guarda_chuva", "galochas"} <= m.roupas)
        self.assertFalse(hasattr(m, "chuva"))                        # o efeito de gotas saiu
        self.assertEqual(len(m.root.winfo_children()), janelas_antes)  # nenhuma janela nova
        self.assertNotIn("chuva_na_tela", m.clima.d)

    def test_trovoada_esconde_e_treme(self):
        m = self.m
        with mock.patch.object(m.clima, "agora_na_cidade", return_value=datetime(2026, 10, 31, 11, 30)):
            self.preparar(com_tempo(95))
            m.mudar("parado", 10)
            m.clima._comportamento(time.time())
            self.assertEqual(m.acao, "tremendo")
            self.assertIn("trovejando", m.balao.texto)
            self.preparar(com_tempo(3))
            m.clima._comportamento(time.time())
            self.assertEqual(m.acao, "parado")

    def test_calor_liga_o_ventilador(self):
        with mock.patch.object(self.m.clima, "agora_na_cidade", return_value=datetime(2026, 10, 31, 11, 30)):
            self.preparar(com_tempo(0, temperatura=33))
        self.assertIsNotNone(self.m.efeitos.ventilador)

    def test_sem_internet_fica_com_o_ultimo(self):
        self.preparar()
        self.preparar(falhar=True)
        self.assertEqual(self.m.clima.atual.temperatura, 22.8)
        self.assertIsNotNone(self.m.clima.erro)
        self.m.clima.mostrar()
        self.assertIn("último", self.m.balao.texto)

    def test_clique_mostra_a_temperatura(self):
        self.preparar()
        self.clicar()
        self.assertIn("23°C", self.m.balao.texto)

    def test_previsao_de_manha_avisa_uma_vez(self):
        m = self.m
        self.preparar()
        m.balao.esconder()
        manha = datetime(2026, 10, 31, 9, 0)
        with mock.patch.object(m.clima, "agora_na_cidade", return_value=manha), \
                mock.patch("pet.clima_controle.tela.segundos_ocioso", return_value=0):
            m.clima._previsao_da_manha()
            self.assertIn("lá pelas 14h (59%)", m.balao.texto)
            m.balao.esconder()
            m.clima._previsao_da_manha()
            self.assertFalse(m.balao.visivel)

    def test_clima_velho_usa_o_relogio_pra_dia_e_noite(self):
        self.preparar()                 # leitura das 11:15, de dia
        with mock.patch.object(self.m.clima, "agora_na_cidade", return_value=datetime(2026, 10, 31, 22, 0)):
            self.assertFalse(self.m.clima.vigente().eh_dia)
            self.assertIn("pijama", self.m.clima.roupas())

    def test_cochilo_da_chuva(self):
        m = self.m
        m.tama.cochilar(60)
        self.assertEqual(m.acao, "dormindo")
        m.tama.cochilo_ate = time.time() - 1
        m.tama._sono(time.time())
        self.assertNotEqual(m.acao, "dormindo")
        self.assertIsNone(m.tama.cochilo_ate)

    def test_menu_mostra_a_temperatura_e_a_pagina_do_clima(self):
        self.preparar()
        self.abrir_menu()
        textos = self.textos_do_menu()
        self.assertTrue(any(t.startswith("23°") for t in textos))
        self.clicar_no_menu("Clima e cidade")
        textos = self.textos_do_menu()
        self.assertIn("Trocar cidade", textos)
        self.assertNotIn("Gotas de chuva na tela", textos)
        self.assertTrue(any("Open-Meteo" in t for t in textos))

    def test_trocar_cidade(self):
        self.assertTrue(self.m.clima.trocar_cidade("Recife, PE"))
        d = self.m.clima.d
        self.assertEqual((d["cidade"], d["estado"], d["lat"]), ("Recife", "Pernambuco", None))


if __name__ == "__main__":
    unittest.main()
