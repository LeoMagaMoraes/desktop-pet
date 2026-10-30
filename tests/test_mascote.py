"""Teste de fumaça: sobe o mascote de verdade (precisa de tela) e simula o mouse."""

import tempfile
import time
import unittest
from pathlib import Path

try:
    import tkinter as tk
    tk.Tk().destroy()
    TEM_TELA = True
except Exception:
    TEM_TELA = False


@unittest.skipUnless(TEM_TELA, "precisa de tela")
class TestMascote(unittest.TestCase):
    def setUp(self):
        from clawd.mascote import Mascote
        self.pasta = tempfile.TemporaryDirectory()
        self.m = Mascote(arquivo_estado=Path(self.pasta.name) / "clawd.json")
        self.m.root.deiconify()
        self.m.root.update()

    def tearDown(self):
        self.m.sair()
        self.pasta.cleanup()

    def evento(self, tipo, x, y, **kw):
        m = self.m
        m.canvas.event_generate(tipo, x=int(x - m.root.winfo_rootx()), y=int(y - m.root.winfo_rooty()),
                                rootx=int(x), rooty=int(y), **kw)

    def rodar_ticks(self, segundos):
        fim = time.perf_counter() + segundos
        while time.perf_counter() < fim:
            agora = time.perf_counter()
            self.m._atualizar(agora, 1 / 30)
            self.m._desenhar(agora)
            self.m.root.update()
            time.sleep(1 / 60)

    def test_clique_da_coracao_e_felicidade(self):
        antes = self.m.estado.status["felicidade"]
        x, y = self.m.corpo.x, self.m.corpo.y - 20
        self.evento("<ButtonPress-1>", x, y)
        self.evento("<ButtonRelease-1>", x + 3, y)       # 3 px: ainda é clique
        self.assertEqual(self.m.estado.status["felicidade"], antes + 2)
        self.assertEqual(len(self.m.efeitos.particulas), 1)
        self.assertNotEqual(self.m.acao, "pendurado")

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
        m.alimentar()
        self.assertEqual(m.acao, "comendo")
        m.dormir()
        self.assertEqual(m.acao, "dormindo")
        x, y = m.corpo.x, m.corpo.y - 10
        self.evento("<ButtonPress-1>", x, y)
        self.evento("<ButtonRelease-1>", x, y)
        self.assertEqual(m.acao, "parado")               # clique acorda
        m.mostrar_status()
        self.assertIn("Fome", m.balao.texto)

    def test_todas_as_animacoes_desenham(self):
        for nome in self.m.sprites.animacoes:
            self.m.mudar(nome)
            self.m._desenhar(time.perf_counter())


if __name__ == "__main__":
    unittest.main()
