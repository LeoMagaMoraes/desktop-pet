"""Troca de pet: registro dos bichos, progresso separado, desenho do dragão e o menu."""

import copy
import json
import tempfile
import time
import unittest
from pathlib import Path

from pet import especies, pixelart as p
from pet.estado import PADRAO, Estado
from tests.test_mascote import BaseMascote


def dados_clawd(**extra):
    d = copy.deepcopy(PADRAO)
    d.update(fase="filhote", xp=340, sujeira=20)
    d["status"].update(fome=50)
    d.update(extra)
    return d


class TestEspecies(unittest.TestCase):
    def test_primeira_vez_vem_um_ovo_e_o_clawd_fica_guardado(self):
        d = dados_clawd()
        self.assertTrue(especies.trocar(d, "dragao"))
        self.assertEqual((d["especie"], d["fase"], d["xp"], d["sujeira"]), ("dragao", "ovo", 0, 0))
        self.assertEqual(d["pets"]["clawd"]["xp"], 340)
        self.assertEqual(d["pets"]["clawd"]["status"]["fome"], 50)

    def test_volta_com_tudo_que_tinha(self):
        d = dados_clawd()
        especies.trocar(d, "dragao")
        d["xp"] = 120
        d["fase"] = "filhote"
        especies.trocar(d, "clawd")
        self.assertEqual((d["especie"], d["xp"], d["fase"], d["status"]["fome"]), ("clawd", 340, "filhote", 50))
        self.assertEqual(d["pets"]["dragao"]["xp"], 120)
        self.assertNotIn("clawd", d["pets"])          # o ativo nunca fica duplicado em "pets"

    def test_trocar_pro_mesmo_ou_desconhecido_nao_faz_nada(self):
        d = dados_clawd()
        self.assertFalse(especies.trocar(d, "clawd"))
        self.assertFalse(especies.trocar(d, "unicornio"))
        self.assertEqual(d["xp"], 340)

    def test_guardado_nao_compartilha_objetos(self):
        d = dados_clawd()
        especies.trocar(d, "dragao")
        d["status"]["fome"] = 1
        self.assertEqual(d["pets"]["clawd"]["status"]["fome"], 50)

    def test_resumo(self):
        d = dados_clawd()
        self.assertEqual(especies.resumo_do_pet(d, "clawd"), ("filhote", 340))
        self.assertIsNone(especies.resumo_do_pet(d, "dragao"))
        especies.trocar(d, "dragao")
        self.assertEqual(especies.resumo_do_pet(d, "clawd"), ("filhote", 340))
        self.assertEqual(especies.resumo_do_pet(d, "dragao"), ("ovo", 0))

    def test_nomes(self):
        self.assertEqual(especies.nome_fase("dragao", "filhote"), "Filhote de dragão")
        self.assertEqual(especies.nome_fase("clawd", "anciao"), "Clawd ancião")
        self.assertEqual(especies.especie("?").id, "clawd")

    def test_save_antigo_continua_sendo_do_clawd(self):
        with tempfile.TemporaryDirectory() as pasta:
            arq = Path(pasta) / "pet.json"
            arq.write_text(json.dumps({"xp": 2000, "fase": "clawd"}), encoding="utf-8")
            d = Estado.carregar(arq).dados
            self.assertEqual((especies.atual(d), d["pets"]), ("clawd", {}))


class TestDesenhoDoDragao(unittest.TestCase):
    def test_tem_todas_as_animacoes_do_clawd(self):
        for fase in p.FASES:
            self.assertEqual(set(p.animacoes(fase, especie="dragao")), set(p.animacoes(fase)), fase)

    def test_quadros_do_tamanho_da_grade(self):
        for fase in p.FASES:
            for nome, (ms, quadros) in p.animacoes(fase, especie="dragao").items():
                for g in quadros:
                    self.assertEqual((g.largura, g.altura), (p.LARGURA, p.ALTURA), f"{fase}/{nome}")
                    self.assertGreater(g.pixels_pintados(), 10, f"{fase}/{nome}")

    def test_em_pe_encosta_no_chao(self):
        for fase in ("filhote", "clawd", "anciao"):
            an = p.animacoes(fase, especie="dragao")
            for nome in ("parado", "andando", "comendo", "comemorando", "acenando", "tonto", "digitando"):
                for g in an[nome][1]:
                    self.assertTrue(any(g.px[-1]), f"{fase}/{nome}")

    def test_e_verde_e_tem_duas_pernas_grossas(self):
        g = p.animacoes("clawd", especie="dragao")["parado"][1][0]
        cores = {c for linha in g.px for c in linha}
        self.assertTrue({p.VERDE, p.BARRIGA, p.CHIFRE} <= cores)
        self.assertNotIn(p.LARANJA, cores)
        self.assertEqual([x for x, c in enumerate(g.px[-1]) if c], [7, 8, 13, 14])

    def test_andando_levanta_uma_perna_de_cada_vez(self):
        an = p.animacoes("clawd", especie="dragao")["andando"][1]
        chao = [[x for x, c in enumerate(g.px[-1]) if c] for g in an]
        self.assertIn([13, 14], chao)       # perna esquerda levantada
        self.assertIn([7, 8], chao)         # perna direita levantada

    def test_asas_sobem_quando_levanta_os_bracos(self):
        an = p.animacoes("clawd", especie="dragao")
        parado, comemorando = an["parado"][1][0], an["comemorando"][1][0]
        topo_da_asa = lambda g: min(y for y, linha in enumerate(g.px) if linha[1] == p.VERDE_SOMBRA)
        self.assertLess(topo_da_asa(comemorando), topo_da_asa(parado))

    def test_ovo_de_dragao_e_verde(self):
        g = p.animacoes("ovo", especie="dragao")["parado"][1][0]
        cores = {c for linha in g.px for c in linha if c}
        self.assertNotIn(p.CASCA, cores)
        self.assertIn(p.VERDE_SOMBRA, cores)

    def test_clawd_continua_igual(self):
        # O desenho genérico não pode ter mudado o Clawd
        g = p.animacoes("clawd")["parado"][1][0]
        self.assertEqual([x for x, c in enumerate(g.px[-1]) if c], [5, 7, 14, 16])
        self.assertIn(p.LARANJA, {c for linha in g.px for c in linha})


class TestDesenhoDoTubarao(unittest.TestCase):
    def test_tem_todas_as_animacoes_e_encosta_no_chao(self):
        for fase in p.FASES:
            self.assertEqual(set(p.animacoes(fase, especie="tubarao")), set(p.animacoes(fase)), fase)
        for fase in ("filhote", "clawd", "anciao"):
            an = p.animacoes(fase, especie="tubarao")
            for nome in ("parado", "andando", "comemorando", "digitando"):
                for g in an[nome][1]:
                    self.assertEqual((g.largura, g.altura), (p.LARGURA, p.ALTURA))
                    self.assertTrue(any(g.px[-1]), f"{fase}/{nome}")

    def test_azul_com_barriga_branca_e_dentinhos(self):
        g = p.animacoes("clawd", especie="tubarao")["parado"][1][0]
        cores = {c for linha in g.px for c in linha}
        self.assertTrue({p.AZUL_TUBARAO, p.BARRIGA_TUBARAO, p.GUELRA} <= cores)
        self.assertNotIn(p.LARANJA, cores)
        boca = g.px[p.DRAGAO_ADULTO.topo + p.DRAGAO_ADULTO.boca_dy]
        self.assertIn(p.BRANCO, boca)            # dentinhos
        self.assertIn(p.PRETO, boca)

    def test_barbatana_acima_do_corpo(self):
        g = p.animacoes("clawd", especie="tubarao")["parado"][1][0]
        acima = [c for linha in g.px[:p.DRAGAO_ADULTO.topo] for c in linha if c]
        self.assertIn(p.AZUL_TUBARAO_SOMBRA, acima)

    def test_ovo_e_uma_capsula_marrom(self):
        g = p.animacoes("ovo", especie="tubarao")["parado"][1][0]
        cores = {c for linha in g.px for c in linha if c}
        self.assertIn("#8C6A4F", cores)

    def test_cada_bicho_tem_icone_e_nomes(self):
        for esp in especies.ESPECIES.values():
            self.assertIn(esp.icone, p.ICONES)
            self.assertEqual(set(esp.nomes_fase), set(p.FASES))
            self.assertIn(esp.id, p.BICHOS)


class TestTrocarPetNaTela(BaseMascote):
    SAVE = {"fase": "filhote", "xp": 340, "status": {"fome": 50, "energia": 80, "felicidade": 80}}

    def test_troca_vira_ovo_de_dragao_com_fumaca(self):
        m = self.m
        m.trocar_pet("dragao")
        self.assertEqual((m.especie, m.fase), ("dragao", "ovo"))
        self.assertEqual(m.sprites.especie, "dragao")
        self.assertIn("ovo de dragão", m.balao.texto)
        self.assertTrue(any(m.canvas.itemcget(pt.item, "image") == str(m.imagens_efeito["fumaca"])
                            for pt in m.efeitos.particulas))

    def test_ida_e_volta(self):
        m = self.m
        m.trocar_pet("dragao")
        m.tama.ganhar_xp(150)
        m.trocar_pet("clawd")
        self.assertEqual((m.especie, m.fase, m.estado.dados["xp"]), ("clawd", "filhote", 340))
        self.assertIn("Oi de novo! Sou o Clawd", m.balao.texto)
        m.trocar_pet("dragao")
        self.assertEqual(m.estado.dados["xp"], 150)

    def test_pet_guardado_fica_pausado(self):
        m = self.m
        m.trocar_pet("dragao")
        m.fase = "filhote"                                   # pra o tempo valer pro dragão
        m.estado.dados["fase"] = "filhote"
        m.tama._ultimo -= 3600
        m.tama._prox_checagem = 0
        m.tama.tick()
        self.assertLess(m.estado.status["fome"], 80)         # o dragão sentiu a hora
        self.assertEqual(m.estado.dados["pets"]["clawd"]["status"]["fome"], 50)   # o Clawd não

    def test_dragao_espirra_faisca(self):
        m = self.m
        m.trocar_pet("dragao")
        m.espirrar()
        self.assertIn("🔥", m.balao.texto)
        self.esperar(lambda: any(m.canvas.itemcget(pt.item, "image") == str(m.imagens_efeito["fogo"])
                                 for pt in m.efeitos.particulas))

    def test_tubarao_espirra_bolhas_e_tem_progresso_proprio(self):
        m = self.m
        m.trocar_pet("dragao")
        m.tama.ganhar_xp(30)
        m.trocar_pet("tubarao")
        self.assertEqual((m.especie, m.fase, m.estado.dados["xp"]), ("tubarao", "ovo", 0))
        self.assertEqual(m.estado.dados["pets"]["dragao"]["xp"], 30)
        self.assertEqual(m.estado.dados["pets"]["clawd"]["xp"], 340)
        m.estado.dados["fase"] = m.fase = "filhote"
        m.espirrar()
        self.assertIn("💦", m.balao.texto)
        self.esperar(lambda: any(m.canvas.itemcget(pt.item, "image") == str(m.imagens_efeito["bolha"])
                                 for pt in m.efeitos.particulas))

    def test_dragao_nasce_com_o_nome_dele(self):
        m = self.m
        m.trocar_pet("dragao")
        m.mudar("parado", 10)
        m.tama.ganhar_xp(100)
        self.assertEqual(m.acao, "chocando")
        self.rodar_ticks(3.3)
        self.assertEqual(m.fase, "filhote")
        self.assertIn("Oi, eu sou o Dragãozinho", m.balao.texto)

    def test_nao_troca_no_ar(self):
        self.m.mudar("caindo")
        self.m.trocar_pet("dragao")
        self.assertEqual(self.m.especie, "clawd")

    def test_menu_de_pets(self):
        m = self.m
        self.abrir_menu()
        self.assertIn("Clawd  ›", self.textos_do_menu())
        self.clicar_no_menu("Trocar de pet")
        textos = self.textos_do_menu()
        self.assertIn("Clawd 🦀", textos)
        self.assertIn("Dragãozinho 🐉", textos)
        self.assertIn("Tubarãozinho 🦈", textos)
        self.assertIn("● agora", textos)
        self.assertIn("novo! 🥚", textos)
        self.clicar_no_menu("Dragãozinho 🐉")
        self.esperar(lambda: m.especie == "dragao")
        self.assertEqual(m.especie, "dragao")
        self.abrir_menu()
        self.assertIn("Ovo de dragão", self.textos_do_menu())
        self.clicar_no_menu("Trocar de pet")
        self.assertIn("Filhote · 340 XP", self.textos_do_menu())


if __name__ == "__main__":
    unittest.main()
