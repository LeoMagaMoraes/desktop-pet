"""Gera o ícone do programa e as imagens do README a partir da pixel art do código.

Uso:  python ferramentas/gerar_imagens.py
Precisa do Pillow (pip install pillow), só pra esta ferramenta; o Clawd em si não usa.

Saída:
  assets/pet.ico         ícone do atalho (16, 32, 48, 64, 128 e 256 px, sem borrar)
  assets/pet.png         o mesmo ícone em 256 px
  docs/clawd.gif         Clawd animado pro topo do README
  docs/fases.png         ovo, filhote, Clawd e ancião lado a lado
  docs/reacoes.png       as reações ao Claude Code
"""

import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from pet import pixelart  # noqa: E402


def rgb(cor):
    return tuple(int(cor[i:i + 2], 16) for i in (1, 3, 5))


def para_pil(grade, escala):
    """Grade -> imagem RGBA com cada pixel virando um quadrado escala x escala."""
    img = Image.new("RGBA", (grade.largura, grade.altura), (0, 0, 0, 0))
    for y, linha in enumerate(grade.px):
        for x, cor in enumerate(linha):
            if cor:
                img.putpixel((x, y), rgb(cor) + (255,))
    return img.resize((grade.largura * escala, grade.altura * escala), Image.NEAREST)


def lado_a_lado(imagens, espaco):
    largura = sum(i.width for i in imagens) + espaco * (len(imagens) - 1)
    altura = max(i.height for i in imagens)
    folha = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    x = 0
    for img in imagens:
        folha.paste(img, (x, altura - img.height), img)     # alinhados pelos pés
        x += img.width + espaco
    return folha


def gerar_icone():
    pasta = RAIZ / "assets"
    pasta.mkdir(exist_ok=True)
    tamanhos = [16, 32, 48, 64, 128, 256]
    imagens = [para_pil(pixelart.ICONE_APP, t // 16) for t in tamanhos]
    imagens[-1].save(pasta / "pet.ico", format="ICO", sizes=[(t, t) for t in tamanhos],
                     append_images=imagens[:-1])
    imagens[-1].save(pasta / "pet.png")
    print("assets/pet.ico e assets/pet.png")


def salvar_gif(quadros, caminho):
    """GIF animado com fundo transparente. quadros: [(imagem RGBA, milissegundos)]."""
    largura = max(q.width for q, _ in quadros)
    altura = max(q.height for q, _ in quadros)
    # Paleta fixa: índice 0 é o transparente, o resto são as cores da pixel art
    cores = sorted({cor[:3] for q, _ in quadros for _, cor in q.getcolors(1 << 16) if cor[3]})
    paleta = [0, 0, 0] + [c for cor in cores for c in cor]
    indice = {cor: i + 1 for i, cor in enumerate(cores)}
    imagens = []
    for q, _ in quadros:
        p = Image.new("P", (largura, altura), 0)
        p.putpalette(paleta)
        ox, oy = (largura - q.width) // 2, altura - q.height
        for y in range(q.height):
            for x in range(q.width):
                px = q.getpixel((x, y))
                if px[3]:
                    p.putpixel((ox + x, oy + y), indice[px[:3]])
        imagens.append(p)
    imagens[0].save(caminho, save_all=True, append_images=imagens[1:], loop=0,
                    duration=[ms for _, ms in quadros], transparency=0, disposal=2)


def gerar_docs():
    pasta = RAIZ / "docs"
    pasta.mkdir(exist_ok=True)
    escala = 8

    # Clawd animado: acena, anda, comemora, digita e cochila
    an = pixelart.animacoes("clawd")
    roteiro = [("acenando", 6), ("andando", 8), ("comemorando", 6), ("digitando", 8), ("dormindo", 4)]
    quadros = []
    for nome, repeticoes in roteiro:
        ms, grades = an[nome]
        for i in range(repeticoes):
            quadros.append((para_pil(grades[i % len(grades)], escala), max(ms, 120)))
    salvar_gif(quadros, pasta / "clawd.gif")

    fases = [para_pil(pixelart.animacoes(f)["parado"][1][0], escala) for f in pixelart.FASES]
    lado_a_lado(fases, 4 * escala).save(pasta / "fases.png")

    nomes = ["comendo", "digitando", "comemorando", "acenando", "caido", "mao_na_cabeca", "empanturrado"]
    reacoes = [para_pil(an[n][1][0], 6) for n in nomes]
    lado_a_lado(reacoes, 24).save(pasta / "reacoes.png")

    # Roupas do clima: sol, nublado, chuva, neve, frio, noite e trovoada (escondido tremendo)
    looks = [{"oculos_sol"}, set(), {"guarda_chuva", "galochas"}, {"gorro", "cachecol"}, {"cachecol"},
             {"pijama"}]
    roupas = [para_pil(pixelart.animacoes("clawd", frozenset(r))["parado"][1][0], 6) for r in looks]
    roupas.append(para_pil(an["tremendo"][1][0], 6))
    lado_a_lado(roupas, 24).save(pasta / "roupas.png")
    # A turma toda, adulta, lado a lado (topo do README)
    turma = [para_pil(pixelart.animacoes("clawd", especie=b)["parado"][1][0], 5) for b in pixelart.BICHOS]
    lado_a_lado(turma, 20).save(pasta / "turma.png")

    # Outros pets: as quatro fases e algumas poses de cada um
    for bicho in [b for b in pixelart.BICHOS if b != "clawd"]:
        fases = [para_pil(pixelart.animacoes(f, especie=bicho)["parado"][1][0], escala) for f in pixelart.FASES]
        lado_a_lado(fases, 4 * escala).save(pasta / f"{bicho}_fases.png")
        ad = pixelart.animacoes("clawd", especie=bicho)
        poses = [para_pil(ad[n][1][0], 6) for n in ("comemorando", "digitando", "acenando", "caido", "dormindo")]
        poses.append(para_pil(pixelart.animacoes("clawd", frozenset({"guarda_chuva", "galochas"}), bicho)
                              ["parado"][1][0], 6))
        lado_a_lado(poses, 24).save(pasta / f"{bicho}_poses.png")
    print("docs/clawd.gif, docs/fases.png, docs/reacoes.png, docs/roupas.png e as fases/poses dos pets")


if __name__ == "__main__":
    gerar_icone()
    gerar_docs()
