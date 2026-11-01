"""Fiscal do git: olha os projetos onde o Claude Code trabalhou e, se tem mudança
parada há muito tempo sem commit, levanta uma plaquinha "commit?".

O git roda numa thread (nunca trava a animação). estado_do_repo e precisa_commit
não dependem do Tk e dá pra testar.
"""

import shutil
import subprocess
import threading
import time
from pathlib import Path

MINUTOS_ENTRE_CHECAGENS = 10
HORAS_SEM_COMMIT = 2            # mudança + último commit mais velho que isso = "commit?"
LINHAS_DEMAIS = 300             # ...ou tanta linha mudada que já vale um commit
MINUTOS_ENTRE_AVISOS = 45       # por projeto
HORAS_PROJETO_RECENTE = 12      # só fiscaliza projeto em que o Claude mexeu nesse tempo


def _git(pasta, *args):
    r = subprocess.run(["git", "-C", str(pasta), *args], capture_output=True, text=True, timeout=10,
                       encoding="utf-8", errors="replace",
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return r.stdout.strip() if r.returncode == 0 else None


def estado_do_repo(pasta):
    """{"raiz", "nome", "arquivos", "linhas", "ultimo_commit"} do repositório da pasta, ou None.

    ultimo_commit é epoch (None se ainda não tem commit); linhas não conta arquivo novo.
    """
    if not pasta or not Path(pasta).is_dir():
        return None
    raiz = _git(pasta, "rev-parse", "--show-toplevel")
    if not raiz:
        return None
    status = _git(raiz, "status", "--porcelain")
    if status is None:
        return None
    info = {"raiz": raiz, "nome": Path(raiz).name, "arquivos": len(status.splitlines()), "linhas": 0,
            "ultimo_commit": None}
    ultimo = _git(raiz, "log", "-1", "--format=%ct")
    if ultimo and ultimo.isdigit():
        info["ultimo_commit"] = int(ultimo)
        resumo = _git(raiz, "diff", "HEAD", "--shortstat") or ""
        # " 3 files changed, 120 insertions(+), 4 deletions(-)"
        for parte in resumo.split(",")[1:]:
            numero = parte.strip().split(" ")[0]
            if numero.isdigit():
                info["linhas"] += int(numero)
    return info


def precisa_commit(info, agora):
    if not info or info["arquivos"] == 0:
        return False
    sem_commit = agora - (info["ultimo_commit"] or 0)
    return sem_commit >= HORAS_SEM_COMMIT * 3600 or info["linhas"] >= LINHAS_DEMAIS


def _tempo(segundos):
    horas = int(segundos // 3600)
    if horas >= 48:
        return f"{horas // 24} dias"
    if horas >= 1:
        return f"{horas} h"
    return f"{max(1, int(segundos // 60))} min"


def frase(info, agora):
    n = info["arquivos"]
    texto = f"📝 commit?\n{info['nome']}: {n} arquivo{'s' if n > 1 else ''} mudado{'s' if n > 1 else ''}"
    if info["ultimo_commit"] is None:
        return texto + "\ne nenhum commit ainda!"
    return texto + f"\núltimo commit há {_tempo(agora - info['ultimo_commit'])}"


# ---------------------------------------------------------------------- ligado ao pet

class FiscalGit:
    def __init__(self, mascote):
        self.m = mascote
        self.d = mascote.estado.dados["claude"]
        self.projetos = {}             # pasta -> quando o Claude mexeu nela por último
        self.avisado = {}              # raiz do repo -> quando avisou
        self.tem_git = shutil.which("git") is not None
        self._resultado = None
        self._thread = None
        self._prox = time.time() + 60

    @property
    def ligado(self):
        return self.d["fiscal_git"] and self.tem_git

    def alternar(self):
        self.d["fiscal_git"] = not self.d["fiscal_git"]

    def viu(self, pasta, terminou=False):
        """Evento do Claude Code numa pasta; no fim de uma task, olha o git logo depois."""
        if not pasta:
            return
        self.projetos[pasta] = time.time()
        if terminou:
            self._prox = min(self._prox, time.time() + 8)     # depois do balão de "Terminei!"

    def tick(self):
        agora = time.time()
        if self._resultado is not None:
            resultado, self._resultado = self._resultado, None
            self._avisar(resultado, agora)
        if not self.ligado or agora < self._prox or (self._thread and self._thread.is_alive()):
            return
        self._prox = agora + MINUTOS_ENTRE_CHECAGENS * 60
        recentes = [p for p, quando in self.projetos.items() if agora - quando < HORAS_PROJETO_RECENTE * 3600]
        if recentes:
            self._thread = threading.Thread(target=self._olhar, args=(recentes,), daemon=True)
            self._thread.start()

    def _olhar(self, pastas):
        achados, raizes = [], set()
        for pasta in pastas:
            try:
                info = estado_do_repo(pasta)
            except (OSError, subprocess.SubprocessError):
                info = None
            if info and info["raiz"] not in raizes:
                raizes.add(info["raiz"])
                achados.append(info)
        self._resultado = achados

    def _avisar(self, achados, agora):
        m = self.m
        if m.cc.ocupado or m.lembretes.ativo is not None or m.acao in ("pendurado", "caindo", "dormindo"):
            return            # não atrapalha o Claude trabalhando (vê de novo na próxima checagem)
        for info in achados:
            if precisa_commit(info, agora) and agora - self.avisado.get(info["raiz"], 0) >= MINUTOS_ENTRE_AVISOS * 60:
                self.avisado[info["raiz"]] = agora
                if m.fase != "ovo" and m.acao in ("parado", "andando", "digitando"):
                    m.mudar("placa", 5)
                m.falar(frase(info, agora), 6)
                return
