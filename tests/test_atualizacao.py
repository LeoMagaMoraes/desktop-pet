"""Atualização pelo git: verificar, instalar, avisar, menu e reiniciar."""

import os
import shutil
import subprocess
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from pet import atualizacao, tela
from tests.test_mascote import BaseMascote

TEM_GIT = shutil.which("git") is not None


def git(pasta, *args):
    subprocess.run(["git", "-C", str(pasta), *args], check=True, capture_output=True)


def commit(pasta, arquivo, texto, titulo):
    (Path(pasta) / arquivo).write_text(texto, encoding="utf-8")
    git(pasta, "add", ".")
    git(pasta, "commit", "-q", "-m", titulo)


@unittest.skipUnless(TEM_GIT, "precisa do git")
class TestVerificarEInstalar(unittest.TestCase):
    """Um "GitHub" de mentira (repo bare), o pet do usuário e outra cópia que publica novidades."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.origem = base / "origem.git"
        git(base, "init", "-q", "--bare", "-b", "main", str(self.origem))
        self.pet = self.clonar("pet")
        commit(self.pet, "a.txt", "um\n", "Primeira versão")
        git(self.pet, "push", "-q", "-u", "origin", "main")
        self.outro = self.clonar("outro")

    def tearDown(self):
        self.tmp.cleanup()

    def clonar(self, nome):
        pasta = Path(self.tmp.name) / nome
        git(self.tmp.name, "clone", "-q", str(self.origem), str(pasta))
        git(pasta, "config", "user.email", "t@t")
        git(pasta, "config", "user.name", "t")
        return pasta

    def publicar(self, *titulos):
        for i, titulo in enumerate(titulos):
            commit(self.outro, f"novo{i}.txt", titulo, titulo)
        git(self.outro, "push", "-q", "origin", "main")

    def test_em_dia(self):
        self.assertEqual(atualizacao.verificar(self.pet)["estado"], "atualizado")

    def test_tem_novidade_e_instala(self):
        self.publicar("Novo pet: lontra", "Bola mais rápida")
        info = atualizacao.verificar(self.pet)
        self.assertEqual(info["estado"], "disponivel")
        self.assertEqual(info["novidades"], 2)
        self.assertEqual(info["titulos"], ["Bola mais rápida", "Novo pet: lontra"])
        self.assertEqual(atualizacao.instalar(self.pet), (True, ""))
        self.assertTrue((self.pet / "novo0.txt").exists())
        self.assertEqual(atualizacao.verificar(self.pet, buscar=False)["estado"], "atualizado")

    def test_arquivo_nao_versionado_nao_atrapalha(self):
        (self.pet / "pet.json").write_text("{}", encoding="utf-8")     # o save fica fora do git
        self.publicar("Novidade")
        self.assertEqual(atualizacao.verificar(self.pet)["estado"], "disponivel")
        self.assertTrue(atualizacao.instalar(self.pet)[0])

    def test_mudanca_local_nao_atualiza_sozinho(self):
        self.publicar("Novidade")
        (self.pet / "a.txt").write_text("mexi\n", encoding="utf-8")
        self.assertEqual(atualizacao.verificar(self.pet)["estado"], "mudancas_locais")

    def test_commit_local_diverge(self):
        self.publicar("Novidade")
        commit(self.pet, "meu.txt", "x", "Meu commit")
        info = atualizacao.verificar(self.pet)
        self.assertEqual(info["estado"], "divergiu")
        ok, _ = atualizacao.instalar(self.pet)
        self.assertFalse(ok)                                # nunca mistura nada

    def test_sem_internet(self):
        self.publicar("Novidade")
        git(self.pet, "remote", "set-url", "origin", str(Path(self.tmp.name) / "nao-existe.git"))
        self.assertEqual(atualizacao.verificar(self.pet)["estado"], "erro")

    def test_pasta_sem_git_ou_sem_origem(self):
        solta = Path(self.tmp.name) / "zip"
        solta.mkdir()
        self.assertEqual(atualizacao.verificar(solta)["estado"], "sem_git")
        local = Path(self.tmp.name) / "local"
        local.mkdir()
        git(local, "init", "-q")
        self.assertEqual(atualizacao.verificar(local)["estado"], "sem_origem")


class TestReabrir(unittest.TestCase):
    def test_comando_espera_o_antigo_fechar(self):
        cmd = atualizacao.comando_pra_reabrir()
        self.assertEqual(cmd[-1], "--reiniciando")
        self.assertTrue(cmd[1].endswith((".py", ".pyw")))
        if Path(cmd[0]).with_name("pythonw.exe").exists():
            self.assertTrue(cmd[0].lower().endswith("pythonw.exe"))   # reabre sem terminal

    @unittest.skipUnless(tela.WINDOWS, "mutex do Windows")
    def test_trava_solta_quando_o_outro_fecha(self):
        nome = f"Local\\PetTeste{os.getpid()}{time.time_ns()}"
        primeiro = tela.instancia_unica(nome)
        self.assertIsNotNone(primeiro)
        self.assertIsNone(tela.instancia_unica(nome))       # já tem um aberto...
        tela._kernel32.CloseHandle(primeiro)                # ...ele fecha...
        segundo = tela.instancia_unica(nome)                # ...e o novo consegue abrir
        self.assertIsNotNone(segundo)
        tela._kernel32.CloseHandle(segundo)


DISPONIVEL = {"estado": "disponivel", "novidades": 3, "titulos": ["Bola", "Fênix", "Loja"]}


class TestAtualizacaoNoPet(BaseMascote):
    def resultado(self, tipo, valor):
        at = self.m.atualizacao
        at._resultado = (tipo, valor)
        at.tick()

    def test_primeira_vez_no_dia_olha_e_avisa(self):
        m = self.m
        at = m.atualizacao
        at._prox = 0
        with mock.patch("pet.atualizacao.verificar", return_value=DISPONIVEL) as verificar:
            at.tick()
            self.esperar(lambda: at._resultado is not None)
            m.balao.esconder()
            at.tick()
            verificar.assert_called_once()
        self.assertEqual(at.d["ultima_checagem"], date.today().isoformat())
        self.assertIn("Saiu versão nova", m.balao.texto)
        self.assertIn("3 novidades", m.balao.texto)
        # Hoje já olhou: não procura de novo
        at._prox = 0
        with mock.patch("pet.atualizacao.verificar") as verificar:
            at.tick()
            verificar.assert_not_called()

    def test_sem_internet_tenta_de_novo_mais_tarde(self):
        at = self.m.atualizacao
        self.resultado("verificar", {"estado": "erro", "erro": "offline"})
        self.assertIsNone(at.d["ultima_checagem"])
        self.assertFalse(at.tem_novidade)

    def test_menu_mostra_atualizar(self):
        self.resultado("verificar", DISPONIVEL)
        self.abrir_menu()
        textos = self.textos_do_menu()
        self.assertIn("Atualizar o P.E.T.", textos)
        self.assertIn("3 novidades", textos)
        self.assertNotIn("Procurar atualização", textos)

    def test_menu_procurar_quando_em_dia(self):
        self.resultado("verificar", {"estado": "atualizado"})
        self.abrir_menu()
        textos = self.textos_do_menu()
        self.assertIn("Procurar atualização", textos)
        self.assertIn("em dia ✓", textos)

    def test_procurar_pelo_menu_conta_que_esta_em_dia(self):
        m = self.m
        with mock.patch("pet.atualizacao.verificar", return_value={"estado": "atualizado"}):
            m.atualizacao.procurar_agora()
            self.esperar(lambda: m.atualizacao._resultado is not None)
        m.atualizacao.tick()
        self.assertIn("versão mais nova", m.balao.texto)

    def test_atualizar_instala_e_reinicia(self):
        m = self.m
        at = m.atualizacao
        self.resultado("verificar", DISPONIVEL)
        with mock.patch("pet.atualizacao.messagebox.askyesno", return_value=True) as pergunta, \
                mock.patch("pet.atualizacao.instalar", return_value=(True, "")), \
                mock.patch.object(at, "reiniciar") as reiniciar:
            at.atualizar()
            self.assertIn("• Bola", pergunta.call_args[0][1])
            self.esperar(lambda: at._resultado is not None)
            at.tick()
            self.assertIn("Reiniciando", m.balao.texto)
            self.esperar(lambda: reiniciar.called, 3)
            reiniciar.assert_called_once()
        self.assertEqual(at.d["acabou_de_atualizar"], ["Bola", "Fênix", "Loja"])
        self.assertIn("Atualizei", at.boas_vindas())
        self.assertIsNone(at.boas_vindas())                  # conta só uma vez

    def test_desistir_de_atualizar(self):
        at = self.m.atualizacao
        self.resultado("verificar", DISPONIVEL)
        with mock.patch("pet.atualizacao.messagebox.askyesno", return_value=False), \
                mock.patch("pet.atualizacao.instalar") as instalar:
            at.atualizar()
        instalar.assert_not_called()
        self.assertFalse(at.ocupado)

    def test_mudanca_local_explica_em_vez_de_atualizar(self):
        at = self.m.atualizacao
        self.resultado("verificar", {**DISPONIVEL, "estado": "mudancas_locais"})
        self.assertIn("atualize pelo git", self.m.balao.texto)
        with mock.patch("pet.atualizacao.messagebox.showinfo") as info, \
                mock.patch("pet.atualizacao.instalar") as instalar:
            at.atualizar()
        info.assert_called_once()
        instalar.assert_not_called()

    def test_falha_ao_instalar_avisa(self):
        self.resultado("verificar", DISPONIVEL)
        self.resultado("instalar", (False, "deu ruim"))
        self.assertIn("Não consegui atualizar", self.m.balao.texto)
        self.assertIsNone(self.m.atualizacao.d["acabou_de_atualizar"])

    def test_reiniciar_abre_o_novo_e_fecha(self):
        m = self.m
        with mock.patch("pet.atualizacao.subprocess.Popen") as popen, mock.patch.object(m, "sair") as sair:
            m.atualizacao.reiniciar()
        self.assertEqual(popen.call_args[0][0][-1], "--reiniciando")
        sair.assert_called_once()


if __name__ == "__main__":
    unittest.main()
