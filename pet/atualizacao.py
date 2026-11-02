"""Atualização: na primeira vez que o pet abre no dia, ele olha no GitHub se saiu
versão nova. Tendo, ele avisa e aparece "Atualizar o P.E.T." no menu: baixa,
instala e reinicia sozinho.

Funciona com o projeto baixado pelo git clone (é o que o README manda fazer):
"baixar" é um git fetch e "instalar" é avançar pro que chegou (só fast-forward,
nunca mistura nem apaga mudança sua). verificar e instalar não dependem do Tk.
"""

import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import date
from pathlib import Path
from tkinter import messagebox

from . import config

log = logging.getLogger(__name__)

SEGUNDOS_ATE_OLHAR = 8          # depois de abrir, espera o "oi" e a internet antes de olhar
MINUTOS_PRA_TENTAR_DE_NOVO = 30  # sem internet: tenta de novo mais tarde no mesmo dia
MAX_TITULOS = 5


def _git(pasta, *args, timeout=30):
    """(código de saída, saída, erro) de um comando git, sem janela e sem pedir senha."""
    r = subprocess.run(["git", "-C", str(pasta), *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def verificar(pasta, buscar=True):
    """Situação do projeto em relação ao GitHub. Devolve {"estado": ...} e, quando tem novidade,
    "novidades" (quantos commits) e "titulos" (os mais novos primeiro).

    estado: "atualizado", "disponivel", "mudancas_locais" (você mexeu nos arquivos do pet),
    "divergiu" (tem commit seu que não está no GitHub), "sem_git", "sem_origem" ou "erro" (sem internet).
    """
    if shutil.which("git") is None:
        return {"estado": "sem_git"}
    try:
        codigo, _, _ = _git(pasta, "rev-parse", "--show-toplevel")
        if codigo:
            return {"estado": "sem_git"}
        codigo, _, _ = _git(pasta, "rev-parse", "--abbrev-ref", "@{u}")
        if codigo:
            return {"estado": "sem_origem"}
        if buscar:
            codigo, _, erro = _git(pasta, "fetch", "--quiet", timeout=60)
            if codigo:
                return {"estado": "erro", "erro": erro}
        _, atras, _ = _git(pasta, "rev-list", "--count", "HEAD..@{u}")
        _, frente, _ = _git(pasta, "rev-list", "--count", "@{u}..HEAD")
    except (OSError, subprocess.SubprocessError) as erro:
        return {"estado": "erro", "erro": str(erro)}
    atras, frente = int(atras or 0), int(frente or 0)
    if atras == 0:
        return {"estado": "atualizado"}
    _, titulos, _ = _git(pasta, "log", "--format=%s", "-n", str(MAX_TITULOS), "HEAD..@{u}")
    info = {"estado": "disponivel", "novidades": atras, "titulos": titulos.splitlines()}
    _, mudou, _ = _git(pasta, "status", "--porcelain", "--untracked-files=no")
    if frente:
        info["estado"] = "divergiu"
    elif mudou:
        info["estado"] = "mudancas_locais"
    return info


def instalar(pasta):
    """Avança o projeto pra versão que chegou. Devolve (deu certo, mensagem de erro)."""
    try:
        codigo, _, erro = _git(pasta, "merge", "--ff-only", "@{u}")
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    return codigo == 0, erro


def comando_pra_reabrir():
    """O mesmo Python (sem terminal, se der) abrindo o mesmo jeito que abriu, esperando o antigo fechar."""
    python = Path(sys.executable)
    sem_terminal = python.with_name("pythonw.exe")
    if sem_terminal.exists():
        python = sem_terminal
    script = Path(sys.argv[0]) if sys.argv and sys.argv[0].endswith((".py", ".pyw")) else None
    if script is None or not script.exists():
        script = config.PASTA_BASE / "pet.pyw"
    return [str(python), str(script.resolve()), "--reiniciando"]


# ---------------------------------------------------------------------- ligado ao pet

class Atualizacao:
    def __init__(self, mascote, pasta=config.PASTA_BASE):
        self.m = mascote
        self.pasta = pasta
        self.d = mascote.estado.dados["atualizacao"]
        self.situacao = None          # resultado do último verificar
        self.avisou = False
        self._thread = None
        self._resultado = None        # ("verificar", info) ou ("instalar", (ok, erro)), vindo da thread
        self._manual = False          # foi você que pediu pelo menu (aí ele conta até se estiver em dia)
        self._prox = time.time() + SEGUNDOS_ATE_OLHAR

    @property
    def ocupado(self):
        return self._thread is not None and self._thread.is_alive()

    @property
    def tem_novidade(self):
        return bool(self.situacao) and self.situacao["estado"] in ("disponivel", "mudancas_locais", "divergiu")

    def rotulo(self):
        """O que aparece do lado do item no menu."""
        if self.ocupado:
            return "procurando..."
        estado = (self.situacao or {}).get("estado")
        return {"atualizado": "em dia ✓", "erro": "sem internet", "sem_git": "precisa do git",
                "sem_origem": "sem GitHub"}.get(estado, "")

    def boas_vindas(self):
        """Depois de reiniciar atualizado: conta o que mudou (uma vez só)."""
        titulos = self.d.get("acabou_de_atualizar")
        if not titulos:
            return None
        self.d["acabou_de_atualizar"] = None
        self.m.salvar()                     # já contou: não repete se fechar antes do autosave
        return "Atualizei! ✨\nNovidade: " + titulos[0][:60]

    # ------------------------------------------------------------------ threads

    def _rodar(self, tipo, funcao):
        def trabalho():
            try:
                self._resultado = (tipo, funcao())
            except Exception as erro:          # nunca derruba o pet por causa da atualização
                log.exception("Erro na atualização")
                self._resultado = (tipo, {"estado": "erro", "erro": str(erro)} if tipo == "verificar"
                                   else (False, str(erro)))
        self._thread = threading.Thread(target=trabalho, daemon=True)
        self._thread.start()

    def procurar_agora(self):
        """Pelo menu."""
        if self.ocupado or self.m.demo:
            return
        self._manual = True
        self.m.falar("Procurando atualização... 🔎", 2)
        self._rodar("verificar", lambda: verificar(self.pasta))

    def atualizar(self):
        """Pelo menu: confirma, baixa/instala numa thread e reinicia."""
        s = self.situacao or {}
        if self.ocupado or not self.tem_novidade:
            return
        if s["estado"] == "mudancas_locais":
            messagebox.showinfo("Atualizar o P.E.T.",
                                "Você mexeu em arquivos do pet, então eu não atualizo sozinho pra não "
                                "estragar nada.\n\nAtualize pelo git (git stash, git pull, git stash pop).",
                                parent=self.m.root)
            return
        if s["estado"] == "divergiu":
            messagebox.showinfo("Atualizar o P.E.T.",
                                "Tem commit seu que não está no GitHub, então eu não atualizo sozinho.\n\n"
                                "Atualize pelo git (git pull).", parent=self.m.root)
            return
        novidades = "\n".join(f"• {t}" for t in s.get("titulos", []))
        if not messagebox.askyesno(
                "Atualizar o P.E.T.",
                f"Saiu versão nova ({s['novidades']} novidade{'s' if s['novidades'] > 1 else ''}):\n\n"
                f"{novidades}\n\nO pet vai baixar, instalar e reiniciar. Atualizar agora?", parent=self.m.root):
            return
        self.m.falar("Atualizando... ⏳", fixo=True)
        self._rodar("instalar", lambda: instalar(self.pasta))

    def reiniciar(self):
        """Abre o pet de novo (o novo espera este fechar) e fecha este."""
        self.m.salvar()
        try:
            subprocess.Popen(comando_pra_reabrir(), cwd=str(config.PASTA_BASE), close_fds=True,
                             creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                             | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        except OSError:
            log.exception("Não consegui reabrir o pet")
            self.m.falar("Atualizei, mas não consegui reabrir 😅\nFecha e abre de novo, por favor", 5)
            return
        self.m.sair()

    # ------------------------------------------------------------------ todo tick

    def tick(self):
        if self.m.demo:
            return
        agora = time.time()
        if self._resultado is not None:
            tipo, valor = self._resultado
            self._resultado = None
            if tipo == "verificar":
                self._verificou(valor, agora)
            else:
                self._instalou(*valor)
        if self.tem_novidade and not self.avisou:
            self._avisar()
        hoje = date.today().isoformat()
        if self.d.get("ultima_checagem") != hoje and agora >= self._prox and not self.ocupado:
            self._prox = agora + MINUTOS_PRA_TENTAR_DE_NOVO * 60
            self._rodar("verificar", lambda: verificar(self.pasta))

    def _verificou(self, info, agora):
        self.situacao = info
        manual, self._manual = self._manual, False
        if info["estado"] != "erro":
            self.d["ultima_checagem"] = date.today().isoformat()   # hoje já olhou: só amanhã de novo
            self.m.salvar()
        if info["estado"] in ("disponivel", "mudancas_locais", "divergiu"):
            self.avisou = False
        elif manual:
            self.m.falar({"atualizado": "Tô na versão mais nova! ✅", "erro": "Sem internet agora 📡",
                          "sem_git": "Pra atualizar sozinho\nprecisa do git instalado",
                          "sem_origem": "Essa pasta não veio do GitHub\n(precisa do git clone)"}
                         .get(info["estado"], "Hm, não consegui ver 🤔"), 3)

    def _avisar(self):
        m = self.m
        if m.balao.visivel or m.lembretes.ativo is not None or m.acao in ("pendurado", "caindo", "dormindo"):
            return
        self.avisou = True
        n = self.situacao.get("novidades", 0)
        texto = f"🆕 Saiu versão nova do P.E.T.!\n{n} novidade{'s' if n > 1 else ''}. Menu → Atualizar"
        if self.situacao["estado"] != "disponivel":
            texto = "🆕 Saiu versão nova do P.E.T.!\nMas você mexeu nos arquivos:\natualize pelo git"
        if m.acao in ("parado", "andando"):
            m.mudar("acenando", 2.5)
        m.falar(texto, 6)

    def _instalou(self, ok, erro):
        m = self.m
        if not ok:
            log.error("Atualização falhou: %s", erro)
            m.falar("Não consegui atualizar 😢\n(veja o pet.log)", 4)
            return
        self.d["acabou_de_atualizar"] = (self.situacao or {}).get("titulos") or ["versão nova"]
        self.situacao = {"estado": "atualizado"}
        m.salvar()
        m.mudar("comemorando", 2)
        m.falar("Atualizado! Reiniciando... 🔄", fixo=True)
        m.root.after(1500, self.reiniciar)
