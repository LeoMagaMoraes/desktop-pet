"""Hook do Claude Code pro pet de desktop.

O Claude Code chama este script nos eventos configurados em
%USERPROFILE%\\.claude\\settings.json e manda o JSON do evento pela entrada.
Ele grava:
  ~/.claude/pet-eventos.jsonl     um evento por linha (o pet lê os novos)
  ~/.claude/pet-status.json       o último evento, com os tokens da sessão
  ~/.claude/pet-cache/            soma parcial de tokens de cada sessão

Nunca escreve nada na saída (no UserPromptSubmit isso iria pro contexto do
Claude) e sempre sai com código 0, pra nunca atrapalhar o Claude Code.
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# O pacote pet fica uma pasta acima deste script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pet import eventos_claude, tokens  # noqa: E402

LIMITE_LOG = 512 * 1024       # acima disso o log de eventos é rotacionado
DIAS_CACHE = 14               # cache de sessões mais velho que isso é apagado


def _gravar_json(caminho, dados):
    temporario = caminho.with_name(f"{caminho.name}.{os.getpid()}.tmp")
    temporario.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    os.replace(temporario, caminho)


def _ler_json(caminho):
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _tokens_da_sessao(base, dados, registro):
    """Soma os tokens do transcript e calcula os gastos da task (prompt -> fim)."""
    transcript = dados.get("transcript_path")
    sessao = str(dados.get("session_id") or "sem-id")
    if not transcript or not Path(transcript).exists():
        return
    pasta_cache = base / "pet-cache"
    pasta_cache.mkdir(exist_ok=True)
    arquivo = pasta_cache / f"{''.join(c for c in sessao if c.isalnum() or c == '-')}.json"
    cache = tokens.atualizar_sessao(transcript, _ler_json(arquivo))
    if registro["evento"] == "prompt":
        cache["inicio_task"] = dict(cache["tokens"])
    elif registro["evento"] == "fim":
        inicio = cache.pop("inicio_task", None)
        registro["tokens_task"] = tokens.diferenca(cache["tokens"], inicio) if inicio else None
        _limpar_cache_velho(pasta_cache)
    registro["tokens_sessao"] = cache["tokens"]
    _gravar_json(arquivo, cache)


def _limpar_cache_velho(pasta):
    limite = time.time() - DIAS_CACHE * 86400
    for arquivo in pasta.glob("*.json"):
        try:
            if arquivo.stat().st_mtime < limite:
                arquivo.unlink()
        except OSError:
            pass


def processar(dados, base):
    registro = eventos_claude.classificar(dados)
    if registro is None:
        return None
    cwd = str(dados.get("cwd") or "")
    registro.update({
        "id": uuid.uuid4().hex,
        "hora": datetime.now().astimezone().isoformat(timespec="seconds"),
        "session_id": dados.get("session_id"),
        "cwd": cwd,
        "projeto": Path(cwd).name if cwd else "",
    })
    if registro["evento"] in ("prompt", "fim"):
        _tokens_da_sessao(base, dados, registro)

    # Log de eventos (rotaciona quando cresce) + foto do último evento
    log = base / "pet-eventos.jsonl"
    try:
        if log.stat().st_size > LIMITE_LOG:
            os.replace(log, log.with_name(log.name + ".old"))
    except OSError:
        pass
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    _gravar_json(base / "pet-status.json", registro)
    return registro


def main():
    try:
        bruto = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        dados = json.loads(bruto) if bruto.strip() else {}
        base = tokens.pasta_claude()
        base.mkdir(parents=True, exist_ok=True)
        processar(dados, base)
    except Exception as erro:
        # Guarda o erro num arquivo em vez de quebrar o Claude Code
        try:
            with open(tokens.pasta_claude() / "pet-hook-erros.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()} {type(erro).__name__}: {erro}\n")
        except OSError:
            pass


if __name__ == "__main__":
    main()
    sys.exit(0)
