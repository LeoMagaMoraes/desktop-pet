"""Traduz o JSON que os hooks do Claude Code recebem nos eventos que o Clawd entende.

Eventos gerados:
  prompt       você mandou um prompt (UserPromptSubmit)
  fim          o Claude terminou a resposta (Stop)
  notificacao  o Claude está esperando você (Notification)
  teste        rodou um comando de teste, com "passou": true/false
  erro         um comando de terminal falhou
"""

import re

FERRAMENTAS_TERMINAL = {"Bash", "PowerShell"}

# Notificações que querem dizer "preciso de você"
NOTIFICACOES_ESPERANDO = {"permission_prompt", "idle_prompt", "elicitation_dialog",
                          "elicitation_url_dialog", "agent_needs_input"}

RE_TESTE = re.compile(r"""(?ix)
    \b(pytest|py\.test|unittest|nose2|tox|jest|vitest|mocha|karma|phpunit|rspec|ctest|Invoke-Pester)\b
  | \b(npm|pnpm|yarn|bun)\s+(run\s+)?test\b
  | \b(go|cargo|dotnet|mvn|gradle|gradlew|deno|mix|swift)\s+test\b
  | \bmake\s+(test|check)\b
  | \bplaywright\s+test\b
""")

# Instalar ferramenta de teste não é rodar teste
RE_INSTALACAO = re.compile(r"(?i)\b(pip3?|uv|poetry|npm|pnpm|yarn|choco|winget|scoop)\s+(install|add|i|uninstall)\b")

# Saída de teste que indica falha mesmo com código de saída 0 (ex.: "| tail" no fim)
RE_FALHA = re.compile(r"""(?mx)
    \b[1-9]\d*\s+(failed|failing|failures?|errors?)\b
  | ^FAILED\b
  | \bFAILED\s+\(
  | \bTests?\s+failed\b
  | ^\s*FAIL\b
""")

RE_CODIGO = re.compile(r"Exit code (-?\d+)")


def eh_teste(comando):
    comando = comando or ""
    return bool(RE_TESTE.search(comando)) and not RE_INSTALACAO.search(comando)


def _comando(dados):
    entrada = dados.get("tool_input")
    if isinstance(entrada, dict):
        return str(entrada.get("command") or "")
    return ""


def _saida(dados):
    resposta = dados.get("tool_response")
    if isinstance(resposta, dict):
        return f"{resposta.get('stdout') or ''}\n{resposta.get('stderr') or ''}"
    return str(resposta or "")


def classificar(dados):
    """Dict com o evento do Clawd, ou None se não for nada que interesse."""
    if not isinstance(dados, dict):
        return None
    nome = dados.get("hook_event_name")
    if nome == "UserPromptSubmit":
        return {"evento": "prompt"}
    if nome == "Stop":
        return {"evento": "fim"}
    if nome == "Notification":
        tipo = dados.get("notification_type") or ""
        return {"evento": "notificacao", "tipo": tipo,
                "esperando": tipo in NOTIFICACOES_ESPERANDO or not tipo,
                "mensagem": str(dados.get("message") or "")[:200]}

    if dados.get("tool_name") not in FERRAMENTAS_TERMINAL:
        return None
    comando = _comando(dados)
    if nome == "PostToolUse":
        if eh_teste(comando):
            return {"evento": "teste", "passou": not RE_FALHA.search(_saida(dados)),
                    "comando": comando[:120]}
        return None
    if nome == "PostToolUseFailure":
        if dados.get("is_interrupt"):
            return None
        if eh_teste(comando):
            return {"evento": "teste", "passou": False, "comando": comando[:120]}
        achado = RE_CODIGO.search(str(dados.get("error") or ""))
        return {"evento": "erro", "comando": comando[:120],
                "codigo": int(achado.group(1)) if achado else None}
    return None
