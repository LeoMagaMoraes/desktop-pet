"""Cores da interface (menu, painel de Status e janelinha de lembrete): modo escuro ou claro.

Cada módulo de interface tem as cores como variáveis do módulo (FUNDO, TEXTO...);
aplicar() troca os valores delas, e as janelas usam as novas quando se redesenham.
"""

TEMAS = {
    "escuro": {
        "FUNDO": "#262422",          # fundo do menu
        "BORDA": "#45403B",
        "DESTAQUE": "#3A3532",       # linha com o mouse em cima
        "TEXTO": "#F5F0E8",
        "APAGADO": "#9A948C",
        "SECAO": "#B8A99A",          # títulos das seções (CUIDAR, VER...)
        "LARANJA": "#D97757",
        "VERMELHO": "#E8455A",
        "VERDE": "#7BC67B",
        "AMARELO": "#F2C14E",
        "AZUL": "#8FB4FF",
        "VAZIO": "#45403B",          # parte vazia das barrinhas
        "PERIGO": "#5A2E2E",         # destaque do Sair, Renascer, apagar lembrete
        "OK": "#2E4A2E",             # destaque do Feito!, Atualizar
        "FUNDO_PAINEL": "#1F1E1D",
        "VAZIO_PAINEL": "#3A3836",
        "CAMPO": "#3A3532",          # caixa de texto da janelinha de lembrete
        "BOLINHA": "#F5F0E8",        # bolinha das chaves liga/desliga
    },
    "claro": {
        "FUNDO": "#FBF8F3",
        "BORDA": "#D9D1C5",
        "DESTAQUE": "#EFE7DB",
        "TEXTO": "#2B2622",
        "APAGADO": "#7D756C",
        "SECAO": "#9A7B62",
        "LARANJA": "#C25F3C",        # um pouco mais escuro pra ler bem no claro
        "VERMELHO": "#C8323F",
        "VERDE": "#3E8E41",
        "AMARELO": "#C2921A",
        "AZUL": "#3E6FC9",
        "VAZIO": "#D3CABD",
        "PERIGO": "#F6DADA",
        "OK": "#DCEFD8",
        "FUNDO_PAINEL": "#FBF8F3",
        "VAZIO_PAINEL": "#E3DBCF",
        "CAMPO": "#FFFFFF",
        "BOLINHA": "#FFFFFF",
    },
}
PADRAO = "escuro"


def cores(nome):
    return TEMAS.get(nome, TEMAS[PADRAO])


def aplicar(nome, *modulos):
    """Põe as cores do tema nas variáveis dos módulos de interface (só nas que eles têm)."""
    for modulo in modulos:
        for chave, valor in cores(nome).items():
            if hasattr(modulo, chave):
                setattr(modulo, chave, valor)
