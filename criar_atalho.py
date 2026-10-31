"""Cria o atalho "Pet" com o ícone do programa.

Uso:
  python criar_atalho.py                 na área de trabalho
  python criar_atalho.py --menu-iniciar  também no Menu Iniciar (dá pra fixar na barra)
  python criar_atalho.py --remover       apaga os atalhos

O atalho abre o pet.pyw com o pythonw.exe (sem janela de terminal).
Rode de novo se mover a pasta do projeto ou trocar de Python.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ICONE = RAIZ / "assets" / "pet.ico"
NOME = "Pet.lnk"
NOME_ANTIGO = "Clawd.lnk"   # de quando o projeto era só o Clawd; é apagado

# O PowerShell cria o .lnk pelo WScript.Shell. Os caminhos vão por variável de
# ambiente pra não ter problema com espaço, acento ou aspas.
SCRIPT_CRIAR = r"""
$pasta = [Environment]::GetFolderPath($env:PET_LOCAL)
$atalho = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $pasta $env:PET_NOME))
$atalho.TargetPath = $env:PET_PYTHONW
$atalho.Arguments = '"' + $env:PET_SCRIPT + '"'
$atalho.WorkingDirectory = $env:PET_PASTA
$atalho.IconLocation = $env:PET_ICONE + ',0'
$atalho.Description = 'Pet de desktop (Clawd e a turma)'
$atalho.Save()
Write-Output (Join-Path $pasta $env:PET_NOME)
"""

SCRIPT_REMOVER = r"""
$caminho = Join-Path ([Environment]::GetFolderPath($env:PET_LOCAL)) $env:PET_NOME
if (Test-Path $caminho) { Remove-Item $caminho; Write-Output $caminho }
"""


def pythonw():
    exe = Path(sys.executable)
    candidato = exe.with_name("pythonw.exe")
    return str(candidato if candidato.exists() else exe)


def powershell(script, local, nome=NOME):
    env = dict(os.environ, PET_LOCAL=local, PET_NOME=nome, PET_PYTHONW=pythonw(),
               PET_SCRIPT=str(RAIZ / "pet.pyw"), PET_PASTA=str(RAIZ), PET_ICONE=str(ICONE))
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
        sys.exit("Falta o assets/pet.ico (gere com: python ferramentas/gerar_imagens.py)")

    locais = ["Desktop"] + (["Programs"] if args.menu_iniciar or args.remover else [])
    for local in locais:
        # O atalho com o nome antigo sai sempre; o novo sai só com --remover
        nomes = [NOME_ANTIGO, NOME] if args.remover else [NOME_ANTIGO]
        for nome in nomes:
            apagado = powershell(SCRIPT_REMOVER, local, nome)
            if apagado:
                print(f"Removido: {apagado}")
        if not args.remover:
            print(f"Atalho criado: {powershell(SCRIPT_CRIAR, local)}")


if __name__ == "__main__":
    main()
