"""Testes de fumaça: sobem o mascote de verdade (precisa de tela) e simulam o mouse."""

import json
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

try:
    import tkinter as tk
    tk.Tk().destroy()
    TEM_TELA = True
except Exception:
    TEM_TELA = False


@unittest.skipUnless(TEM_TELA, "precisa de tela")
class BaseMascote(unittest.TestCase):
    SAVE = {"fase": "clawd", "xp": 1000}

    def setUp(self):
        from clawd.mascote import Mascote
        self.pasta = tempfile.TemporaryDirectory()
        arquivo = Path(self.pasta.name) / "clawd.json"
        arquivo.write_text(json.dumps(self.SAVE), encoding="utf-8")
        self.m = Mascote(arquivo_estado=arquivo)
        self.m.root.deiconify()
        self.m.root.update()

    def tearDown(self):
        self.m.painel.fechar()
        self.m.sair()
        self.pasta.cleanup()

    def evento(self, tipo, x, y, **kw):
        m = self.m
        m.canvas.event_generate(tipo, x=int(x - m.root.winfo_rootx()), y=int(y - m.root.winfo_rooty()),
                                rootx=int(x), rooty=int(y), **kw)

    def clicar(self):
        x, y = self.m.corpo.x, self.m.corpo.y - 20
        self.evento("<ButtonPress-1>", x, y)
        self.evento("<ButtonRelease-1>", x + 3, y)       # 3 px: ainda é clique

    def rodar_ticks(self, segundos):
        fim = time.perf_counter() + segundos
        while time.perf_counter() < fim:
            agora = time.perf_counter()
            self.m._atualizar(agora, 1 / 30)
            self.m._desenhar(agora)
            self.m.root.update()
            time.sleep(1 / 60)


class TestMascote(BaseMascote):
    def test_clique_da_coracao_e_felicidade(self):
        self.m.estado.status["felicidade"] = 50
        self.clicar()
        self.assertEqual(self.m.estado.status["felicidade"], 52)
        self.assertEqual(len(self.m.efeitos.particulas), 1)
        self.assertNotEqual(self.m.acao, "pendurado")
        self.assertEqual(self.m.estado.dados["xp"], 1001)

    def test_arrastar_pendura_e_soltar_cai(self):
        m = self.m
        x, y = m.corpo.x, m.corpo.y - 20
        self.evento("<ButtonPress-1>", x, y)
        for i in range(1, 11):
            self.evento("<Motion>", x, y - i * 20, state=0x100)
        self.assertEqual(m.acao, "pendurado")
        self.assertAlmostEqual(m.corpo.y, m.area.base - 200, delta=1)
        time.sleep(0.15)                                  # parou o mouse antes de soltar
        self.evento("<ButtonRelease-1>", x, y - 200)
        self.assertEqual(m.acao, "caindo")
        self.assertEqual((m.corpo.vx, m.corpo.vy), (0, 0))
        self.rodar_ticks(1.5)
        self.assertNotEqual(m.acao, "caindo")
        self.assertEqual(m.corpo.y, m.area.base)
        self.assertEqual(m.estado.dados["lugar_favorito"]["y"], m.area.base)

    def test_menu_acoes(self):
        m = self.m
        m.estado.status["fome"] = 50
        m.alimentar()
        self.assertEqual(m.acao, "comendo")
        self.assertEqual(m.estado.status["fome"], 75)
        m.dormir()
        self.assertEqual(m.acao, "dormindo")
        self.clicar()
        self.assertEqual(m.acao, "parado")               # clique acorda
        m.mostrar_status()
        self.assertTrue(m.painel.aberto)
        m.root.update()

    def test_barriga_cheia_recusa_comida(self):
        self.m.estado.status["fome"] = 100
        self.m.alimentar()
        self.assertNotEqual(self.m.acao, "comendo")
        self.assertIn("cheio", self.m.balao.texto)

    def test_remedio_cura(self):
        m = self.m
        m.estado.dados["doente"] = True
        m.dar_remedio()
        self.assertFalse(m.estado.dados["doente"])
        m.espirrar()
        self.assertEqual(m.acao, "espirrando")

    def test_esfregar_limpa(self):
        m = self.m
        m.estado.dados["sujeira"] = 30
        x, y = m.corpo.x, m.corpo.y - 20
        for i in range(400):
            m.tama.esfregar(x + (40 if i % 2 else -40), y)
        self.assertEqual(m.estado.dados["sujeira"], 0)
        self.assertIn("Cheirosinho", m.balao.texto)

    def test_mosquinhas_quando_sujo(self):
        m = self.m
        m.estado.dados["sujeira"] = 90
        m.tama._moscas()
        self.assertEqual(len(m.efeitos.moscas), 3)
        m.estado.dados["sujeira"] = 0
        m.tama._moscas()
        self.assertEqual(len(m.efeitos.moscas), 0)

    def test_modo_desligado_pausa_status(self):
        m = self.m
        m.tama.mudar_modo(False)
        antes = dict(m.estado.status)
        m.tama._ultimo -= 3600                           # finge que passou 1 hora
        m.tama._prox_checagem = 0
        m.tama.tick()
        self.assertEqual(m.estado.status, antes)
        m.alimentar()                                    # ainda anima, mas não mexe no status
        self.assertEqual(m.estado.status, antes)

        m.tama.mudar_modo(True)
        m.tama._ultimo -= 3600
        m.tama._prox_checagem = 0
        m.tama.tick()
        self.assertLess(m.estado.status["fome"], antes["fome"])

    def test_sem_energia_dorme_sozinho(self):
        m = self.m
        m.estado.status["energia"] = 5
        m.mudar("parado", 10)
        m.tama._sono(time.time())
        self.assertEqual(m.acao, "dormindo")

    def test_todas_as_animacoes_desenham(self):
        for nome in self.m.sprites.animacoes:
            self.m.mudar(nome)
            self.m._desenhar(time.perf_counter())


class TestOvo(BaseMascote):
    SAVE = {"fase": "ovo", "xp": 0}

    def test_ovo_nao_come_nem_anda(self):
        m = self.m
        m.alimentar()
        self.assertNotEqual(m.acao, "comendo")
        for _ in range(20):
            m._decidir_proxima()
            self.assertEqual(m.acao, "parado")

    def test_ovo_nao_tem_status_mudando(self):
        self.assertFalse(self.m.tama.ativo)

    def test_choca_e_vira_filhote(self):
        m = self.m
        m.mudar("parado", 10)
        m.tama.ganhar_xp(100)
        self.assertEqual(m.acao, "chocando")
        self.rodar_ticks(3.3)
        self.assertEqual(m.fase, "filhote")
        self.assertEqual(m.estado.dados["fase"], "filhote")
        self.assertEqual(m.acao, "comemorando")
        self.assertIn("Nasci", m.balao.texto)


class TestOffline(BaseMascote):
    dez_horas_atras = (datetime.now().astimezone() - timedelta(hours=10)).isoformat(timespec="seconds")
    SAVE = {"fase": "clawd", "xp": 1000, "status": {"fome": 80, "energia": 50, "felicidade": 80},
            "ultimo_save": dez_horas_atras}

    def test_desconta_o_tempo_fora(self):
        s = self.m.estado.status
        self.assertAlmostEqual(s["fome"], 60, delta=0.5)
        self.assertAlmostEqual(s["felicidade"], 60, delta=0.5)
        self.assertEqual(s["energia"], 100)
        self.assertIn("Senti sua falta", self.m.tama.boas_vindas())


class TestDoisMonitores(BaseMascote):
    """Simula um segundo monitor à esquerda do principal."""

    def setUp(self):
        from clawd import tela
        from tests.test_tela import ESQUERDA
        self.tela = tela
        self.original = tela.monitores
        principal = tela.monitores()[0]
        self.lista = [principal, ESQUERDA]
        tela.monitores = lambda root=None: self.lista
        super().setUp()

    def tearDown(self):
        super().tearDown()
        self.tela.monitores = self.original

    def test_comeca_no_principal(self):
        self.assertTrue(self.m.monitor.principal)

    def test_menu_lista_os_dois(self):
        m = self.m
        m._atualizar_menu()
        self.assertEqual(m.menu_monitores.index("end"), 1)
        self.assertEqual(m.menu.entrycget(m.INDICE_MONITOR, "state"), "normal")
        self.assertIn("Monitor", m.menu.entrycget(m.INDICE_MONITOR, "label"))

    def test_trocar_pelo_menu(self):
        m = self.m
        m.trocar_monitor(self.lista[1].nome)
        self.assertEqual(m.area, self.lista[1].area)
        self.assertEqual(m.acao, "caindo")
        self.assertLess(m.corpo.x, 0)
        self.rodar_ticks(2)
        self.assertNotEqual(m.acao, "caindo")
        self.assertEqual(m.corpo.y, self.lista[1].area.base)
        self.assertEqual(m.estado.dados["monitor"], self.lista[1].nome)
        self.assertLess(m.root.winfo_x(), 0)            # a janela foi mesmo pra coordenada negativa

    def test_soltar_em_outro_monitor_muda_de_casa(self):
        m = self.m
        x, y = m.corpo.x, m.corpo.y - 20
        self.evento("<ButtonPress-1>", x, y)
        self.evento("<Motion>", x - 10, y - 10, state=0x100)
        self.evento("<Motion>", -300, 600, state=0x100)
        time.sleep(0.15)
        self.evento("<ButtonRelease-1>", -300, 600)
        self.assertEqual(m.monitor.nome, self.lista[1].nome)
        self.rodar_ticks(2)
        self.assertEqual(m.corpo.y, self.lista[1].area.base)
        self.assertEqual(m.estado.dados["monitor"], self.lista[1].nome)

    def test_monitor_desligado_volta_pro_principal(self):
        m = self.m
        m.trocar_monitor(self.lista[1].nome)
        self.lista.pop()                                 # desplugou
        m._reler_area()
        self.assertTrue(m.monitor.principal)
        self.assertEqual(m.acao, "caindo")


class TestUmMonitor(BaseMascote):
    def test_submenu_desativado_com_um_monitor(self):
        from clawd import tela
        if len(tela.monitores()) > 1:
            self.skipTest("este PC tem mais de um monitor")
        self.m._atualizar_menu()
        self.assertEqual(self.m.menu.entrycget(self.m.INDICE_MONITOR, "state"), "disabled")


class TestOfflineDesligado(BaseMascote):
    SAVE = dict(TestOffline.SAVE, modo_tamagotchi=False)

    def test_modo_desligado_nao_desconta(self):
        self.assertEqual(self.m.estado.status["fome"], 80)
        self.assertIsNone(self.m.tama.boas_vindas())


if __name__ == "__main__":
    unittest.main()
