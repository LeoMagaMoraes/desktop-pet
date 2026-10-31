"""Contador de tokens lendo os transcripts .jsonl do Claude Code. Sem Tk.

Cada resposta do Claude aparece em várias linhas do .jsonl com o mesmo
message.id e o mesmo bloco `usage`, então cada id é contado uma vez só.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

# Campos do bloco usage -> nome curto que a gente usa
CAMPOS = {
    "input_tokens": "entrada",
    "output_tokens": "saida",
    "cache_creation_input_tokens": "cache_criacao",
    "cache_read_input_tokens": "cache_leitura",
}
SEMANA = 7 * 24 * 3600


def zerado():
    return {nome: 0 for nome in CAMPOS.values()}


def somar(a, b):
    return {k: a.get(k, 0) + b.get(k, 0) for k in CAMPOS.values()}


def diferenca(depois, antes):
    return {k: max(0, depois.get(k, 0) - antes.get(k, 0)) for k in CAMPOS.values()}


def total(t, so_io=False):
    """Soma de tudo, ou só entrada + saída (o cache costuma ser a maior parte)."""
    if so_io:
        return t.get("entrada", 0) + t.get("saida", 0)
    return sum(t.get(k, 0) for k in CAMPOS.values())


def formatar(n):
    """12345 -> '12.3k', 4500000 -> '4.5M'."""
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(int(n))


def ler_numero(texto):
    """'20M' -> 20000000, '800k' -> 800000, '1.5m' -> 1500000. Vazio ou 0 -> None."""
    texto = (texto or "").strip().lower().replace(",", ".").replace(" ", "")
    if not texto:
        return None
    mult = 1
    if texto[-1] in "kmb":
        mult = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}[texto[-1]]
        texto = texto[:-1]
    valor = int(float(texto) * mult)
    if valor < 0:
        raise ValueError("negativo")
    return valor or None


def extrair(linha):
    """(id, timestamp em segundos, tokens) de uma linha de resposta do Claude, ou None."""
    # Atalho barato: só faz json.loads em linha que pode ter usage
    if '"usage"' not in linha or '"assistant"' not in linha:
        return None
    try:
        o = json.loads(linha)
    except ValueError:
        return None
    msg = o.get("message")
    if o.get("type") != "assistant" or not isinstance(msg, dict):
        return None
    uso = msg.get("usage")
    ident = msg.get("id")
    if not isinstance(uso, dict) or not ident:
        return None
    t = {curto: int(uso.get(longo) or 0) for longo, curto in CAMPOS.items()}
    return ident, _segundos(o.get("timestamp")), t


def _segundos(iso):
    if not iso:
        return 0.0
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _ler_linhas_novas(caminho, offset):
    """Linhas completas a partir de offset e o novo offset (ignora a última se estiver pela metade)."""
    with open(caminho, "rb") as f:
        f.seek(offset)
        bruto = f.read()
    fim = bruto.rfind(b"\n")
    if fim < 0:
        return [], offset
    pedaco = bruto[:fim + 1]
    return pedaco.decode("utf-8", errors="replace").splitlines(), offset + len(pedaco)


def atualizar_sessao(caminho, cache):
    """Soma incremental do transcript de uma sessão.

    cache: {"offset", "ids": [...], "tokens": {...}} (vazio na primeira vez).
    Devolve o cache atualizado; o total da sessão fica em cache["tokens"].
    """
    caminho = Path(caminho)
    if not cache or caminho.stat().st_size < cache.get("offset", 0):
        cache = {"offset": 0, "ids": [], "tokens": zerado()}   # arquivo novo ou reescrito
    vistos = set(cache["ids"])
    linhas, cache["offset"] = _ler_linhas_novas(caminho, cache["offset"])
    for linha in linhas:
        achado = extrair(linha)
        if achado and achado[0] not in vistos:
            vistos.add(achado[0])
            cache["ids"].append(achado[0])
            cache["tokens"] = somar(cache["tokens"], achado[2])
    return cache


class ContadorSemana:
    """Tokens de todos os transcripts deste PC nos últimos 7 dias.

    Guarda o que já leu de cada arquivo (por offset), então as próximas
    contagens só leem o que foi acrescentado. Arquivos não modificados nos
    últimos 7 dias nem são abertos.
    """

    def __init__(self, pasta):
        self.pasta = Path(pasta)
        self._arquivos = {}       # caminho -> {"offset", "mensagens": {id: (ts, tokens)}}
        self.ultima_atividade = 0.0

    def contar(self, agora=None):
        agora = agora or time.time()
        limite = agora - SEMANA
        vivos = set()
        for caminho in self.pasta.rglob("*.jsonl") if self.pasta.is_dir() else ():
            try:
                info = caminho.stat()
            except OSError:
                continue
            self.ultima_atividade = max(self.ultima_atividade, info.st_mtime)
            if info.st_mtime < limite:
                continue                      # velho demais: nem abre
            vivos.add(caminho)
            dados = self._arquivos.get(caminho)
            if dados is None or info.st_size < dados["offset"]:
                dados = self._arquivos[caminho] = {"offset": 0, "mensagens": {}}
            if info.st_size == dados["offset"]:
                continue
            try:
                linhas, dados["offset"] = _ler_linhas_novas(caminho, dados["offset"])
            except OSError:
                continue
            for linha in linhas:
                achado = extrair(linha)
                if achado:
                    dados["mensagens"][achado[0]] = (achado[1], achado[2])

        # Esquece arquivos que saíram da janela e junta tudo sem repetir id
        for caminho in list(self._arquivos):
            if caminho not in vivos:
                del self._arquivos[caminho]
        unicas = {}
        for dados in self._arquivos.values():
            for ident, (ts, t) in dados["mensagens"].items():
                if ts >= limite:
                    unicas[ident] = t
        soma = zerado()
        for t in unicas.values():
            soma = somar(soma, t)
        return soma


def pasta_claude():
    """%USERPROFILE%\\.claude (PET_PASTA_CLAUDE troca a pasta, usado nos testes)."""
    if os.environ.get("PET_PASTA_CLAUDE"):
        return Path(os.environ["PET_PASTA_CLAUDE"])
    return Path(os.environ.get("USERPROFILE") or Path.home()) / ".claude"
