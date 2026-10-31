"""Instala (ou remove) os hooks do Clawd em %USERPROFILE%\\.claude\\settings.json.

Uso:
  python instalar_hooks.py            instala/atualiza
  python instalar_hooks.py --remover  tira só os hooks do Clawd

Mantém todo o resto do settings.json (outros hooks inclusive) e guarda um
backup em settings.json.bak-clawd antes da primeira mudança.
Rode de novo se mudar a pasta do projeto ou a versão do Python.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from clawd.tokens import pasta_claude

SCRIPT = Path(__file__).resolve().parent / "hooks" / "clawd_hook.py"
MARCA = "clawd_hook.py"   # como a gente reconhece os nossos hooks

# evento -> matcher (None = evento sem matcher)
EVENTOS = {
    "UserPromptSubmit": None,
    "Stop": None,
    "Notification": None,
    "PostToolUse": "Bash|PowerShell",
    "PostToolUseFailure": "Bash|PowerShell",
}


def python_sem_janela():
    """pythonw.exe ao lado do python atual (não pisca janela de terminal)."""
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    return str(pythonw if pythonw.exists() else exe)


def eh_nosso(handler):
    return MARCA in json.dumps(handler)


def remover_nossos(hooks):
    """Tira os handlers do Clawd e os grupos que ficarem vazios."""
    for evento in list(hooks):
        grupos = []
        for grupo in hooks[evento]:
            restantes = [h for h in grupo.get("hooks", []) if not eh_nosso(h)]
            if restantes:
                grupos.append(dict(grupo, hooks=restantes))
        if grupos:
            hooks[evento] = grupos
        else:
            del hooks[evento]


def adicionar_nossos(hooks, python, script):
    for evento, matcher in EVENTOS.items():
        grupo = {"hooks": [{
            "type": "command",
            "command": python,       # formato exec: roda o .exe direto, sem shell
            "args": [script],
            "timeout": 15,
        }]}
        if matcher:
            grupo = {"matcher": matcher, **grupo}
        hooks.setdefault(evento, []).append(grupo)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--remover", action="store_true")
    args = parser.parse_args()

    arquivo = pasta_claude() / "settings.json"
    config = {}
    if arquivo.exists():
        try:
            config = json.loads(arquivo.read_text(encoding="utf-8"))
        except ValueError as erro:
            sys.exit(f"settings.json está com JSON inválido, não mexi em nada: {erro}")
        backup = arquivo.with_name("settings.json.bak-clawd")
        if not backup.exists():
            shutil.copy2(arquivo, backup)
            print(f"Backup: {backup}")

    hooks = config.setdefault("hooks", {})
    remover_nossos(hooks)
    if args.remover:
        if not hooks:
            del config["hooks"]
        print("Hooks do Clawd removidos.")
    else:
        adicionar_nossos(hooks, python_sem_janela(), str(SCRIPT))
        print(f"Hooks do Clawd instalados ({', '.join(EVENTOS)}).")
        print(f"  {python_sem_janela()} {SCRIPT}")

    temporario = arquivo.with_name("settings.json.tmp-clawd")
    temporario.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporario.replace(arquivo)


if __name__ == "__main__":
    main()
