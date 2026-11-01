"""Os pets que dá pra ter, o jeito de cada um e a troca entre eles.

Cada pet tem o seu próprio progresso (XP, fase, necessidades). O pet ativo
fica nos campos de sempre do pet.json; os outros ficam guardados em
dados["pets"], pausados, até você trocar de volta.
"""

import copy
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Especie:
    id: str
    nome: str            # como ele se apresenta ("Oi, eu sou o ...")
    emoji: str
    nomes_fase: dict     # fase -> nome que aparece no menu e no painel
    espirro: str         # efeito do espirro: "gota", "fogo", "bolha", "floco", "pena", "feno" ou "folha"
    icone: str           # ícone do menu (pixelart.ICONES)
    artigo: str = "o"    # "o Clawd", "a Fênix"
    # Personalidade (tudo opcional)
    gosta_de_frio: bool = False     # pinguim: frio alegra, calor cansa
    noturno: bool = False           # coruja: dorme de dia, fica esperta de noite
    renasce: bool = False           # fênix: felicidade zerada vira cinzas e renasce do ovo
    calor: int = 30                 # acima disso aparece o ventiladorzinho
    frases: dict = field(default_factory=dict)   # troca falas padrão: "erro", "teste_falhou", "clique",
                                                 # "comida", "prompt", "ovo", "nasci", "popcorn"
    som_clique: str = None          # som ao fazer carinho (sons.MELODIAS)
    som_comida: str = None          # som quando ganha comida ou um prompt
    popcorn: bool = False           # porquinho-da-índia: dá pulinhos de alegria no carinho quando tá feliz
    comilao: bool = False           # fome cai mais rápido, mas comer alegra mais
    dorminhoco: bool = False        # coala: cansa mais, cochila mais e dorme mais cedo
    escalador: bool = False         # coala: sobe nas janelas bem mais vezes
    gosta_de_colo: bool = False     # coala: ser pego no mouse vira abraço (e alegra)

    @property
    def apresentacao(self):
        return f"{self.artigo} {self.nome}"


ESPECIES = {
    "clawd": Especie("clawd", "Clawd", "🦀",
                     {"ovo": "Ovo", "filhote": "Filhote", "clawd": "Clawd", "anciao": "Clawd ancião"},
                     espirro="gota", icone="clawd"),
    "dragao": Especie("dragao", "Dragãozinho", "🐉",
                      {"ovo": "Ovo de dragão", "filhote": "Filhote de dragão", "clawd": "Dragão",
                       "anciao": "Dragão ancião"},
                      espirro="fogo", icone="dragao"),
    "tubarao": Especie("tubarao", "Tubarãozinho", "🦈",
                       {"ovo": "Ovo de tubarão", "filhote": "Filhote de tubarão", "clawd": "Tubarão",
                        "anciao": "Tubarão ancião"},
                       espirro="bolha", icone="tubarao"),
    "pinguim": Especie("pinguim", "Pinguinzinho", "🐧",
                       {"ovo": "Ovo de pinguim", "filhote": "Filhote de pinguim", "clawd": "Pinguim",
                        "anciao": "Pinguim ancião"},
                       espirro="floco", icone="pinguim", gosta_de_frio=True, calor=25),
    "pato": Especie("pato", "Patinho de borracha", "🦆",
                    {"ovo": "Ovo de pato", "filhote": "Filhote de pato", "clawd": "Pato de borracha",
                     "anciao": "Pato ancião"},
                    espirro="bolha", icone="pato", som_clique="quack",
                    frases={"erro": "Já explicou o problema pra mim?\nLinha por linha 🦆",
                            "teste_falhou": "💀 Teste falhou...\nMe conta o que ele faz, devagar 🦆",
                            "clique": "Quack! 🦆"}),
    "fenix": Especie("fenix", "Fênix", "🔥",
                     {"ovo": "Ovo de fênix", "filhote": "Filhote de fênix", "clawd": "Fênix",
                      "anciao": "Fênix anciã"},
                     espirro="fogo", icone="fenix", artigo="a", renasce=True),
    "coruja": Especie("coruja", "Corujinha", "🦉",
                      {"ovo": "Ovo de coruja", "filhote": "Filhote de coruja", "clawd": "Coruja",
                       "anciao": "Coruja anciã"},
                      espirro="pena", icone="coruja", artigo="a", noturno=True),
    "porquinho": Especie("porquinho", "Porquinho-da-índia", "🐹",
                         {"ovo": "Ninho de feno", "filhote": "Filhote de porquinho", "clawd": "Porquinho-da-índia",
                          "anciao": "Porquinho ancião"},
                         espirro="feno", icone="porquinho", som_comida="wheek", popcorn=True, comilao=True,
                         frases={"comida": "Wheek wheek! 🥕", "prompt": "🥕 Prompt novo! Wheek wheek!",
                                 "ovo": "Um ninho de feno! 🌾\nFaz carinho pra ele sair",
                                 "nasci": "Saí do ninho! 🌾\nOi, eu sou o Porquinho-da-índia! 🐹",
                                 "popcorn": "Pop! Pop! 🍿"}),
    "coala": Especie("coala", "Coala", "🐨",
                     {"ovo": "Bolsinha", "filhote": "Filhote de coala", "clawd": "Coala", "anciao": "Coala ancião"},
                     espirro="folha", icone="coala", dorminhoco=True, escalador=True, gosta_de_colo=True,
                     frases={"comida": "Nham... eucalipto! 🌿",
                             "prompt": "🌿 Prompt novo! Eucalipto fresquinho!",
                             "ovo": "Um filhote na bolsinha! 👜\nFaz carinho pra ele sair",
                             "nasci": "Saí da bolsinha! \nOi, eu sou o Coala! 🐨",
                             "clique": "Zzz... ah, oi! 🐨",
                             "colo": "Abraço! 🤗"}),
}
PADRAO = "clawd"

# O que é de cada pet (o resto do save, como clima, monitor e Claude Code, é de todos)
CAMPOS_DO_PET = ("status", "xp", "xp_gasto", "fase", "sujeira", "doente", "horas_com_fome")
PET_NOVO = {"status": {"fome": 80, "energia": 80, "felicidade": 80}, "xp": 0, "xp_gasto": 0, "fase": "ovo",
            "sujeira": 0, "doente": False, "horas_com_fome": 0.0}


def especie(id_):
    return ESPECIES.get(id_, ESPECIES[PADRAO])


def nome_fase(id_, fase):
    return especie(id_).nomes_fase.get(fase, fase)


def atual(dados):
    return dados.get("especie") if dados.get("especie") in ESPECIES else PADRAO


def resumo_do_pet(dados, id_):
    """(fase, xp) de um pet, esteja ele ativo ou guardado (None se nunca foi adotado)."""
    if id_ == atual(dados):
        return dados["fase"], dados["xp"]
    guardado = dados.get("pets", {}).get(id_)
    if not guardado:
        return None
    return guardado["fase"], guardado["xp"]


def trocar(dados, novo):
    """Guarda o pet ativo e traz o `novo` (um ovo se for a primeira vez). Devolve True se trocou."""
    velho = atual(dados)
    if novo == velho or novo not in ESPECIES:
        return False
    pets = dados.setdefault("pets", {})
    pets[velho] = {campo: copy.deepcopy(dados[campo]) for campo in CAMPOS_DO_PET}
    chegando = pets.pop(novo, None) or copy.deepcopy(PET_NOVO)
    for campo in CAMPOS_DO_PET:
        dados[campo] = copy.deepcopy(chegando.get(campo, PET_NOVO[campo]))
    dados["especie"] = novo
    return True


# ---------------------------------------------------------------------- personalidade x clima

FRIO = 15
QUENTE_PRO_PINGUIM = 25


def ajustar_roupas(id_, roupas, c):
    """As roupas do clima, do jeito de cada bicho."""
    esp = especie(id_)
    r = set(roupas)
    if c is None:
        return frozenset(r)
    if esp.gosta_de_frio:
        r -= {"cachecol", "gorro"}               # pinguim não precisa de agasalho
    if esp.noturno:
        r.discard("oculos_sol")
        if c.eh_dia:
            r.add("pijama")                      # coruja dorme de dia...
        else:
            r.discard("pijama")                  # ...e passa a noite acordada
    return frozenset(r)


def ajustar_efeitos(id_, efeitos, c):
    """Como o tempo mexe nas necessidades, do jeito de cada bicho."""
    esp = especie(id_)
    e = dict(efeitos)
    if esp.comilao:
        e["mult_fome"] *= 1.3                    # porquinho-da-índia vive com fome
    if esp.dorminhoco:
        e["dorminhoco"] = True                   # coala dorme quase o dia todo
        e["mult_energia"] *= 1.25
    if c is None:
        return e
    if esp.gosta_de_frio:
        if c.temperatura < FRIO:
            e["mult_fome"] = 1.0                 # frio não dá fome extra...
            e["bonus_felicidade"] += 4.0         # ...dá alegria
        elif c.temperatura > QUENTE_PRO_PINGUIM:
            e["mult_energia"] *= 1.3             # calor cansa
    if esp.noturno:
        if c.eh_dia:
            e["mult_energia"] *= 1.4             # de dia ela tá morrendo de sono
            e["dorminhoco"] = True
        else:
            e["mult_energia"] *= 0.6             # de noite ela tá a mil
            e["bonus_felicidade"] += 2.0
    return e
