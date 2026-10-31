"""Cria o atalho "Clawd" com o ícone do caranguejinho.

Uso:
  python criar_atalho.py                 na área de trabalho
  python criar_atalho.py --menu-iniciar  também no Menu Iniciar (dá pra fixar na barra)
  python criar_atalho.py --remover       apaga os atalhos

O atalho abre o clawd.pyw com o pythonw.exe (sem janela de terminal).
Rode de novo se mover a pasta do projeto ou trocar de Python.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ICONE = RAIZ / "assets" / "clawd.ico"
NOME = "Clawd.lnk"

# O PowerShell cria o .lnk pelo WScript.Shell. Os caminhos vão por variável de
# ambiente pra não ter problema com espaço, acento ou aspas.
SCRIPT_CRIAR = r"""
$pasta = [Environment]::GetFolderPath($env:CLAWD_LOCAL)
$atalho = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $pasta $env:CLAWD_NOME))
$atalho.TargetPath = $env:CLAWD_PYTHONW
$atalho.Arguments = '"' + $env:CLAWD_SCRIPT + '"'
$atalho.WorkingDirectory = $env:CLAWD_PASTA
$atalho.IconLocation = $env:CLAWD_ICONE + ',0'
$atalho.Description = 'Clawd, o caranguejinho do Claude Code'
$atalho.Save()
Write-Output (Join-Path $pasta $env:CLAWD_NOME)
"""

SCRIPT_REMOVER = r"""
$caminho = Join-Path ([Environment]::GetFolderPath($env:CLAWD_LOCAL)) $env:CLAWD_NOME
if (Test-Path $caminho) { Remove-Item $caminho; Write-Output $caminho }
"""


def pythonw():
    exe = Path(sys.executable)
    candidato = exe.with_name("pythonw.exe")
    return str(candidato if candidato.exists() else exe)


def powershell(script, local):
    env = dict(os.environ, CLAWD_LOCAL=local, CLAWD_NOME=NOME, CLAWD_PYTHONW=pythonw(),
               CLAWD_SCRIPT=str(RAIZ / "clawd.pyw"), CLAWD_PASTA=str(RAIZ), CLAWD_ICONE=str(ICONE))
    script = "[Console]::OutputEncoding = [Text.Encoding]::UTF8\n" + script   # acentos de "Área de Trabalho"
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                       env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit(f"Não consegui mexer no atalho:\n{r.stderr.strip()}")
    return r.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--menu-iniciar", action="store_true", help="cria também no Menu Iniciar")
    parser.add_argument("--remover", action="store_true", help="apaga os atalhos")
    args = parser.parse_args()

    if sys.platform != "win32":
        sys.exit("Atalho só existe no Windows.")
    if not ICONE.exists():
        sys.exit("Falta o assets/clawd.ico (gere com: python ferramentas/gerar_imagens.py)")

    locais = ["Desktop"] + (["Programs"] if args.menu_iniciar or args.remover else [])
    for local in locais:
        if args.remover:
            apagado = powershell(SCRIPT_REMOVER, local)
            if apagado:
                print(f"Removido: {apagado}")
        else:
            print(f"Atalho criado: {powershell(SCRIPT_CRIAR, local)}")


if __name__ == "__main__":
    main()
