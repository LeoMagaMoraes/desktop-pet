"""Fase 5: datas especiais, hora de dormir, tela cheia, fiscal do git, resumo do dia, música e loja."""

import os
import subprocess
import tempfile
import time
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

from pet import datas, fiscal_git, hora_dormir, loja, musica, pixelart, resumo
from tests.test_mascote import BaseMascote


class TestDatas(unittest.TestCase):
    def test_pascoa(self):
        self.assertEqual(datas.pascoa(2024), date(2024, 3, 31))
        self.assertEqual(datas.pascoa(2025), date(2025, 4, 20))
        self.assertEqual(datas.pascoa(2026), date(2026, 4, 5))
        self.assertEqual(datas.pascoa(2027), date(2027, 3, 28))

    def test_ocasioes(self):
        o = lambda d, aniv=None: (datas.ocasiao(d, aniv) or datas.Ocasiao("", "", None, "")).id
        self.assertEqual(o(date(2026, 12, 25)), "natal")
        self.assertEqual(o(date(2026, 12, 24)), "natal")
        self.assertEqual(o(date(2026, 12, 31)), "reveillon")
        self.assertEqual(o(date(2027, 1, 1)), "ano_novo")
        self.assertEqual(o(date(2026, 10, 31)), "halloween")
        self.assertEqual(o(date(2026, 4, 5)), "pascoa")
        self.assertEqual(o(date(2026, 2, 16)), "carnaval")      # segunda
        self.assertEqual(o(date(2026, 2, 17)), "carnaval")      # terça
        self.assertEqual(o(date(2026, 9, 13)), "programador")   # dia 256
        self.assertEqual(o(date(2028, 9, 12)), "programador")   # ano bissexto
        self.assertEqual(o(date(2026, 11, 4)), "")

    def test_aniversario_ganha_de_tudo(self):
        self.assertEqual(datas.ocasiao(date(2026, 12, 25), (25, 12)).id, "aniversario")
        self.assertEqual(datas.ocasiao(date(2026, 3, 7), (7, 3)).id, "aniversario")
        # 29/02 comemora no 28 quando o ano não é bissexto
        self.assertEqual(datas.ocasiao(date(2026, 2, 28), (29, 2)).id, "aniversario")
        self.assertIsNone(datas.ocasiao(date(2032, 2, 28), (29, 2)))     # bissexto: espera o 29
        self.assertEqual(datas.ocasiao(date(2032, 2, 29), (29, 2)).id, "aniversario")

    def test_ler_aniversario(self):
        self.assertEqual(datas.ler_aniversario("25/03"), (25, 3))
        self.assertEqual(datas.ler_aniversario(" 5-1 "), (5, 1))
        self.assertEqual(datas.ler_aniversario("29/2"), (29, 2))
        for ruim in ("", "31/02", "13/13", "amanhã", "25/03/1990"):
            self.assertIsNone(datas.ler_aniversario(ruim), ruim)

    def test_roupas_das_datas_existem(self):
        for o in datas.OCASIOES.values():
            self.assertTrue(o.roupa is None or o.roupa in pixelart.CHAPEUS, o.id)


class TestHoraDeDormir(unittest.TestCase):
    def test_ler(self):
        self.assertEqual(hora_dormir.ler("23h"), "23:00")
        self.assertEqual(hora_dormir.ler("22:30"), "22:30")
        self.assertEqual(hora_dormir.ler("meia-noite"), "00:00")
        self.assertIsNone(hora_dormir.ler("cedo"))

    def test_passou_da_hora(self):
        p = lambda h, m, alvo: hora_dormir.passou_da_hora(datetime(2026, 11, 4, h, m), alvo)
        self.assertFalse(p(22, 59, "23:00"))
        self.assertTrue(p(23, 0, "23:00"))
        self.assertTrue(p(2, 0, "23:00"))         # madrugada ainda é "depois da hora"
        self.assertFalse(p(5, 0, "23:00"))        # 5h: já é de manhã
        self.assertFalse(p(14, 0, "23:00"))
        self.assertTrue(p(0, 30, "00:00"))
        self.assertTrue(p(1, 30, "01:00"))
        self.assertFalse(p(23, 30, "01:00"))


class TestResumo(unittest.TestCase):
    def test_dia_cheio(self):
        t = resumo.texto({"minutos_pc": 320, "carinhos": 15, "comidas": 3, "brincadeiras": 0},
                         {"tasks": 12, "tokens": 3_400_000, "testes_ok": 8, "testes_falha": 2,
                          "projetos": ["Tamagochi", "site", "api", "app"]})
        self.assertIn("5h20 no PC", t)
        self.assertIn("12 tasks · 3.4M tokens", t)
        self.assertIn("✅ 8 testes ok · ❌ 2 falharam", t)
        self.assertIn("📁 Tamagochi, site, api +1", t)
        self.assertIn("♥ 15 carinhos · 🍤 3 comidas", t)
        self.assertNotIn("brincadeiras", t)
        self.assertIn("produtivo", t)

    def test_dia_vazio(self):
        self.assertIn("Dia tranquilo", resumo.texto({}, {}))

    def test_muita_tela(self):
        self.assertIn("descansa", resumo.texto({"minutos_pc": 9 * 60}, {}))


def _git(pasta, *args, **env):
    subprocess.run(["git", "-C", str(pasta), *args], check=True, capture_output=True,
                   env={**os.environ, **env})


@unittest.skipUnless(fiscal_git.shutil.which("git"), "precisa do git")
class TestFiscalGit(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.repo = Path(self.pasta.name) / "meu-projeto"
        self.repo.mkdir()
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "user.email", "t@t")
        _git(self.repo, "config", "user.name", "t")

    def tearDown(self):
        self.pasta.cleanup()

    def commitar(self, quando):
        (self.repo / "a.txt").write_text("um\n", encoding="utf-8")
        _git(self.repo, "add", ".")
        data = f"@{int(quando)} -0300"
        _git(self.repo, "commit", "-q", "-m", "x", GIT_AUTHOR_DATE=data, GIT_COMMITTER_DATE=data)

    def test_fora_de_repo(self):
        self.assertIsNone(fiscal_git.estado_do_repo(self.pasta.name))
        self.assertIsNone(fiscal_git.estado_do_repo(None))

    def test_mudanca_velha_pede_commit(self):
        agora = time.time()
        self.commitar(agora - 3 * 3600)
        (self.repo / "a.txt").write_text("um\ndois\n", encoding="utf-8")
        (self.repo / "novo.txt").write_text("oi", encoding="utf-8")
        sub = self.repo / "sub"
        sub.mkdir()
        info = fiscal_git.estado_do_repo(sub)               # de uma subpasta acha a raiz
        self.assertEqual(info["nome"], "meu-projeto")
        self.assertEqual(info["arquivos"], 2)
        self.assertEqual(info["linhas"], 1)
        self.assertTrue(fiscal_git.precisa_commit(info, agora))
        frase = fiscal_git.frase(info, agora)
        self.assertIn("commit?", frase)
        self.assertIn("2 arquivos mudados", frase)
        self.assertIn("há 3 h", frase)

    def test_commit_recente_ou_limpo_nao_pede(self):
        agora = time.time()
        self.commitar(agora - 600)
        self.assertFalse(fiscal_git.precisa_commit(fiscal_git.estado_do_repo(self.repo), agora))   # limpo
        (self.repo / "a.txt").write_text("mudou\n", encoding="utf-8")
        self.assertFalse(fiscal_git.precisa_commit(fiscal_git.estado_do_repo(self.repo), agora))   # recente

    def test_muita_linha_pede_mesmo_recente(self):
        agora = time.time()
        self.commitar(agora - 600)
        (self.repo / "a.txt").write_text("x\n" * 400, encoding="utf-8")
        self.assertTrue(fiscal_git.precisa_commit(fiscal_git.estado_do_repo(self.repo), agora))

    def test_repo_sem_commit(self):
        (self.repo / "a.txt").write_text("oi", encoding="utf-8")
        info = fiscal_git.estado_do_repo(self.repo)
        self.assertIsNone(info["ultimo_commit"])
        self.assertTrue(fiscal_git.precisa_commit(info, time.time()))
        self.assertIn("nenhum commit", fiscal_git.frase(info, time.time()))


class TestDetectorDeMusica(unittest.TestCase):
    def test_som_curto_nao_e_musica(self):
        d = musica.DetectorDeMusica()
        for i in range(8):                       # 2 s de bipe
            d.medir(0.5, i * 0.25)
        self.assertFalse(d.tocando)

    def test_som_seguido_vira_musica_e_para_no_silencio(self):
        d = musica.DetectorDeMusica()
        t = 0.0
        for _ in range(20):                      # 5 s de som, com um buraquinho no meio
            d.medir(0.0 if 2 < t < 3 else 0.3, t)
            t += 0.25
        self.assertTrue(d.tocando)
        for _ in range(20):                      # 5 s de silêncio: ainda conta (pausa entre faixas)
            d.medir(0.0, t)
            t += 0.25
        self.assertTrue(d.tocando)
        for _ in range(16):
            d.medir(0.0, t)
            t += 0.25
        self.assertFalse(d.tocando)


class TestLojaItens(unittest.TestCase):
    def test_itens_existem_na_arte(self):
        for item in loja.ITENS.values():
            self.assertIn(item.lugar, ("cabeca", "rosto", "pescoco"))
            if item.lugar == "cabeca":
                self.assertIn(item.id, pixelart.CHAPEUS)
            elif item.lugar == "rosto":
                self.assertIn(item.id, pixelart.OCULOS)

    def test_vestir_resolve_conflitos(self):
        v = pixelart.vestir("anciao", {"gorro_natal", "coroa", "gorro", "oculos_coracao", "oculos_sol",
                                       "gravata", "cachecol", "pijama"})
        self.assertIn("gorro_natal", v)
        self.assertNotIn("coroa", v)
        self.assertNotIn("cartola", v)
        self.assertNotIn("gorro", v)
        self.assertIn("pijama", v)                # o pijama fica (é roupa), só a touca some
        self.assertIn("oculos_sol", v)
        self.assertNotIn("oculos_coracao", v)
        self.assertNotIn("oculos", v)
        self.assertNotIn("gravata", v)
        self.assertEqual(pixelart.vestir("anciao", {"coroa"}) & {"coroa", "cartola"}, {"coroa"})

    def test_acessorios_mudam_o_desenho(self):
        for bicho in pixelart.BICHOS:
            base = pixelart.animacoes("clawd", especie=bicho)["parado"][1][0].px
            for nome in [*loja.ITENS, "fone", "gorro_natal", "chapeu_festa", "chapeu_bruxa", "orelhas_coelho"]:
                g = pixelart.animacoes("clawd", frozenset({nome}), bicho)["parado"][1][0]
                self.assertNotEqual(g.px, base, (bicho, nome))

    def test_novas_animacoes(self):
        for bicho in pixelart.BICHOS:
            for fase in ("filhote", "clawd", "anciao"):
                an = pixelart.animacoes(fase, especie=bicho)
                for nome in ("bocejando", "dancando", "placa"):
                    self.assertIn(nome, an)


# ---------------------------------------------------------------------- no pet de verdade

class TestRotinaNoPet(BaseMascote):
    def test_loja_compra_usa_e_tira(self):
        m = self.m
        m.estado.dados.update(xp=1000, xp_gasto=0)
        self.assertEqual(m.loja.saldo(), 1000)
        self.assertIn("Comprei", m.loja.escolher("coroa"))
        self.assertEqual(m.loja.saldo(), 200)
        self.assertEqual(m.estado.dados["xp"], 1000)          # a evolução não muda
        self.assertIn("coroa", m.roupas)
        self.assertIn("Faltam", m.loja.escolher("oculos_coracao"))   # 300 > 200
        self.assertIn("Comprei", m.loja.escolher("laco"))      # troca o chapéu
        self.assertEqual(m.loja.vestidos(), {"laco"})
        m.loja.escolher("coroa")                               # já tem: só põe de volta, de graça
        self.assertEqual(m.loja.saldo(), 50)
        self.assertEqual(m.loja.vestidos(), {"coroa"})
        self.assertIn("Guardei", m.loja.escolher("coroa"))
        self.assertEqual(m.loja.vestidos(), set())
        self.assertNotIn("coroa", m.roupas)

    def test_loja_e_de_todos_mas_o_gasto_e_de_cada_um(self):
        m = self.m
        m.estado.dados.update(xp=1000, xp_gasto=0)
        m.loja.escolher("bone")
        m.trocar_pet("dragao")
        self.assertEqual(m.loja.saldo(), 0)                    # ovo novo: sem XP
        self.assertIn("bone", m.loja.vestidos())               # mas o guarda-roupa é o mesmo
        m.trocar_pet("clawd")
        self.assertEqual(m.loja.saldo(), 750)

    def test_pagina_da_loja(self):
        self.m.estado.dados.update(xp=1000, xp_gasto=0)
        self.abrir_menu()
        self.clicar_no_menu("Loja")
        textos = self.textos_do_menu()
        self.assertIn("Coroa 👑", textos)
        self.assertIn("⭐ 800 XP", textos)
        self.clicar_no_menu("Flor 🌸")
        self.assertIn("✓ usando", self.textos_do_menu())
        self.assertTrue(self.m.menu.aberto)

    def test_pagina_rotina(self):
        self.abrir_menu()
        self.clicar_no_menu("Rotina e datas")
        textos = self.textos_do_menu()
        for t in ("Hora de dormir", "Seu aniversário", "Sumir em tela cheia", "Dançar com música",
                  "Resumo do dia às 18h"):
            self.assertIn(t, textos)
        self.clicar_no_menu("Dançar com música")
        self.assertTrue(self.m.estado.dados["rotina"]["musica"])

    def test_aniversario_comemora_uma_vez(self):
        m = self.m
        hoje = date.today()
        self.assertTrue(m.datas.definir_aniversario(f"{hoje.day}/{hoje.month}"))
        self.assertFalse(m.datas.definir_aniversario("31/02"))
        m.balao.esconder()
        m.mudar("parado", 5)
        m.datas._prox = 0
        m.datas.tick()
        self.assertEqual(m.datas.atual.id, "aniversario")
        self.assertIn("chapeu_festa", m.roupas)
        self.assertIn("aniversário", m.balao.texto)
        self.assertEqual(m.acao, "comemorando")
        self.assertGreater(len(m.efeitos.particulas), 5)       # confete
        m.balao.esconder()
        m.datas._prox = 0
        m.datas.tick()
        self.assertFalse(m.balao.visivel)                      # só uma vez por dia

    def test_hora_de_dormir(self):
        m = self.m
        self.assertTrue(m.hora_dormir.definir("23h"))
        self.assertFalse(m.hora_dormir.definir("tarde"))
        noite = datetime(2026, 11, 4, 23, 30)
        m.balao.esconder()
        m.mudar("parado", 5)
        with mock.patch("pet.hora_dormir.datetime") as dt, mock.patch("pet.tela.segundos_ocioso", return_value=5):
            dt.now.return_value = noite
            m.hora_dormir.tick()
        self.assertIn("23:00", m.balao.texto)
        self.assertEqual(m.acao, "bocejando")
        # Saiu do PC: ele dorme
        m.mudar("parado", 5)
        m.hora_dormir._prox = 0
        with mock.patch("pet.hora_dormir.datetime") as dt, mock.patch("pet.tela.segundos_ocioso", return_value=900):
            dt.now.return_value = noite
            m.hora_dormir.tick()
        self.assertEqual(m.acao, "dormindo")

    def test_tela_cheia_esconde_e_volta(self):
        m = self.m
        m.estado.dados["rotina"]["tela_cheia"] = True
        with mock.patch("pet.tela.tela_cheia_em", return_value=True):
            m.tela_cheia.tick()
        self.assertTrue(m.tela_cheia.escondido)
        self.assertEqual(m.root.state(), "withdrawn")
        m.falar("Oi")
        self.assertFalse(m.balao.visivel)                      # quietinho enquanto escondido
        m.tela_cheia._prox = 0
        with mock.patch("pet.tela.tela_cheia_em", return_value=False):
            m.tela_cheia.tick()
        self.assertFalse(m.tela_cheia.escondido)
        self.assertEqual(m.root.state(), "normal")

    def test_lembrete_fura_a_tela_cheia(self):
        m = self.m
        m.estado.dados["rotina"]["tela_cheia"] = True
        with mock.patch("pet.tela.tela_cheia_em", return_value=True):
            m.tela_cheia.tick()
            m.lembretes.ativo = {"id": "x", "texto": "Reunião"}
            m.tela_cheia._prox = 0
            m.tela_cheia.tick()
        self.assertFalse(m.tela_cheia.escondido)

    def test_fiscal_levanta_a_placa(self):
        m = self.m
        info = {"raiz": "C:/proj", "nome": "proj", "arquivos": 3, "linhas": 10, "ultimo_commit": time.time() - 4 * 3600}
        m.balao.esconder()
        m.mudar("parado", 5)
        m.fiscal._resultado = [info]
        m.fiscal.tick()
        self.assertEqual(m.acao, "placa")
        self.assertIn("commit?", m.balao.texto)
        # Não repete logo em seguida
        m.balao.esconder()
        m.fiscal._resultado = [info]
        m.fiscal.tick()
        self.assertFalse(m.balao.visivel)

    def test_fiscal_nao_atrapalha_o_claude_trabalhando(self):
        m = self.m
        m.cc.trabalhando["s"] = time.time()
        m.balao.esconder()
        m.fiscal._resultado = [{"raiz": "r", "nome": "r", "arquivos": 1, "linhas": 0, "ultimo_commit": None}]
        m.fiscal.tick()
        self.assertFalse(m.balao.visivel)

    def test_fiscal_anota_projetos_do_claude(self):
        self.hook(evento="fim", cwd="C:/algum/projeto", projeto="projeto")
        self.assertIn("C:/algum/projeto", self.m.fiscal.projetos)

    def test_resumo_conta_cuidados(self):
        m = self.m
        m.estado.status["fome"] = 40
        self.clicar()
        m.alimentar()
        m.resumo.mostrar()
        self.assertIn("♥ 1 carinho · 🍤 1 comida", m.balao.texto)

    def test_musica_poe_fone_e_dança(self):
        m = self.m
        m.estado.dados["rotina"]["musica"] = True
        m.musica._parar.set()                                  # sem thread de verdade
        m.musica.detector.tocando = True
        m.musica.tick()
        self.assertTrue(m.musica.ativa)
        self.assertIn("fone", m.roupas)
        with mock.patch("random.random", return_value=0.1):
            m._decidir_proxima()
        self.assertEqual(m.acao, "dancando")
        m.musica._prox_nota = 0
        m.musica.tick()
        self.assertTrue(any(m.canvas.itemcget(p.item, "image") for p in m.efeitos.particulas))
        m.musica.detector.tocando = False
        m.musica._prox = 0
        m.musica.tick()
        self.assertNotIn("fone", m.roupas)
        self.assertNotEqual(m.acao, "dancando")


if __name__ == "__main__":
    unittest.main()
