"""Loja: acessórios comprados com XP.

Comprar não tira evolução: o XP total continua (é ele que decide a fase) e o que
foi gasto fica separado em "xp_gasto". O guarda-roupa é de todos os pets, mas
quem paga é o pet que está na tela.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    id: str              # nome do acessório em pixelart
    nome: str
    emoji: str
    preco: int
    lugar: str           # "cabeca", "rosto" ou "pescoco": só um item por lugar


ITENS = {i.id: i for i in (
    Item("flor", "Flor", "🌸", 100, "cabeca"),
    Item("laco", "Laço", "🎀", 150, "cabeca"),
    Item("gravata", "Gravata-borboleta", "🤵", 200, "pescoco"),
    Item("bone", "Boné", "🧢", 250, "cabeca"),
    Item("oculos_coracao", "Óculos de coração", "😍", 300, "rosto"),
    Item("coroa", "Coroa", "👑", 800, "cabeca"),
)}


class Loja:
    def __init__(self, mascote):
        self.m = mascote
        dados = mascote.estado.dados
        a = dados.get("acessorios")
        if not isinstance(a, dict):
            a = dados["acessorios"] = {}
        a["comprados"] = [i for i in a.get("comprados", []) if i in ITENS]
        a["equipados"] = {lugar: i for lugar, i in (a.get("equipados") or {}).items()
                          if i in a["comprados"] and ITENS[i].lugar == lugar}
        self.a = a

    def saldo(self):
        d = self.m.estado.dados
        return d["xp"] - d.get("xp_gasto", 0)

    def comprado(self, ident):
        return ident in self.a["comprados"]

    def usando(self, ident):
        return ident in self.a["equipados"].values()

    def vestidos(self):
        return set(self.a["equipados"].values())

    def escolher(self, ident):
        """Clique num item: compra (se der), põe ou tira. Devolve o que o pet fala."""
        item = ITENS[ident]
        m = self.m
        equipados = self.a["equipados"]
        if self.usando(ident):
            del equipados[item.lugar]
            fala = f"Guardei: {item.nome} {item.emoji}"
        elif self.comprado(ident):
            equipados[item.lugar] = ident
            fala = f"Que tal? {item.emoji}"
        else:
            falta = item.preco - self.saldo()
            if falta > 0:
                return f"Faltam {falta} XP\npra {item.nome.lower()} 💸"
            m.estado.dados["xp_gasto"] = m.estado.dados.get("xp_gasto", 0) + item.preco
            self.a["comprados"].append(ident)
            equipados[item.lugar] = ident
            fala = f"Comprei! {item.emoji}✨"
            if m.acao in ("parado", "andando"):
                m.mudar("comemorando", 2)
        m.atualizar_roupas()
        m.salvar()
        return fala
