"""Carrega os quadros de cada animação: PNGs da pasta sprites/ ou o Clawd provisório.

Procura, nesta ordem:
  sprites/<fase>/<animacao>/*.png   (fases: ovo, filhote, clawd, anciao)
  sprites/<animacao>/*.png          (só pra fase clawd, o adulto)
  sprites/<bicho>/...               (o mesmo esquema pros outros pets, ex.: sprites/dragao/)
  desenho provisório de pixelart.py
Os PNGs são lidos em ordem alfabética e devem estar virados pra direita.
Um anim.json opcional na pasta define a velocidade: {"ms": 120}
"""

import json
import logging
import tkinter as tk

from . import pixelart

log = logging.getLogger(__name__)


def grade_para_imagem(root, grade, escala):
    img = tk.PhotoImage(master=root, width=grade.largura, height=grade.altura)
    for y, linha in enumerate(grade.px):
        for x, cor in enumerate(linha):
            if cor:
                img.put(cor, to=(x, y))
    # Zoom inteiro mantém o pixel nítido e a transparência
    return img.zoom(escala)


def criar_imagens_efeito(root, escala):
    """Coração, Zzz, mosquinha etc. Ficam fora da biblioteca porque não mudam com a fase."""
    escala_efeito = max(2, escala - 1)
    return {nome: grade_para_imagem(root, g, escala_efeito) for nome, g in pixelart.EFEITOS.items()}


class BibliotecaSprites:
    def __init__(self, root, escala, pasta, fase="clawd", roupas=frozenset(), especie="clawd"):
        self.root = root
        self.escala = escala
        self.pasta = pasta
        self.fase = fase
        self.especie = especie
        self.roupas = frozenset(roupas)   # roupas do clima (só no desenho provisório)
        self._de_grade = {}      # id(grade) -> imagem (quadros repetidos usam a mesma)
        self._espelhadas = {}    # id(imagem) -> imagem virada pra esquerda
        self.usando_png = set()
        self.animacoes = {}      # nome -> (ms, quadros_direita, quadros_esquerda)

        for nome, (ms, grades) in pixelart.animacoes(fase, self.roupas, especie).items():
            png = self._carregar_pngs(nome)
            if png:
                quadros, ms = png[0], png[1] or ms
                self.usando_png.add(nome)
            else:
                quadros = [self._da_grade(g) for g in grades]
            self.animacoes[nome] = (ms, quadros, [self._espelhar(q) for q in quadros])

    # --- tamanhos usados pra montar a janela e a física ---

    @property
    def largura_max(self):
        return max(q.width() for _, qs, _ in self.animacoes.values() for q in qs)

    @property
    def altura_max(self):
        return max(q.height() for _, qs, _ in self.animacoes.values() for q in qs)

    @property
    def altura_corpo(self):
        """Distância dos pés ao topo da cabeça, em pixels de tela."""
        if "parado" in self.usando_png:
            return round(self.animacoes["parado"][1][0].height() * 0.9)
        return pixelart.medidas(self.fase, self.especie)[0] * self.escala

    @property
    def meia_largura(self):
        """Metade da largura do corpo com os bracinhos (pra bater nas bordas)."""
        if "parado" in self.usando_png:
            return round(self.animacoes["parado"][1][0].width() * 0.4)
        return pixelart.medidas(self.fase, self.especie)[1] * self.escala

    def quadro(self, nome, ms_desde_inicio, virado_esquerda=False):
        """Imagem da animação no instante pedido."""
        ms, direita, esquerda = self.animacoes[nome]
        quadros = esquerda if virado_esquerda else direita
        return quadros[int(ms_desde_inicio // ms) % len(quadros)]

    # --- conversões ---

    def _da_grade(self, grade):
        if id(grade) not in self._de_grade:
            self._de_grade[id(grade)] = grade_para_imagem(self.root, grade, self.escala)
        return self._de_grade[id(grade)]

    def _espelhar(self, img):
        if id(img) not in self._espelhadas:
            self._espelhadas[id(img)] = img.subsample(-1, 1)  # x negativo espelha no Tk
        return self._espelhadas[id(img)]

    def _carregar_pngs(self, nome):
        # O Clawd usa sprites/ direto; os outros bichos, sprites/<bicho>/
        raiz = self.pasta if self.especie == "clawd" else self.pasta / self.especie
        pastas = [raiz / self.fase / nome]
        if self.fase == "clawd":                     # adulto também aceita as pastas soltas
            pastas.append(raiz / nome)
        for pasta in pastas:
            arquivos = sorted(pasta.glob("*.png")) if pasta.is_dir() else []
            if not arquivos:
                continue
            try:
                quadros = [self._ajustar_tamanho(tk.PhotoImage(master=self.root, file=str(a)))
                           for a in arquivos]
                ms = None
                config = pasta / "anim.json"
                if config.exists():
                    ms = int(json.loads(config.read_text(encoding="utf-8")).get("ms", 0)) or None
                log.info("Sprites PNG: %s (%d quadros)", pasta, len(quadros))
                return quadros, ms
            except (tk.TclError, OSError, ValueError) as erro:
                log.warning("Não deu pra ler %s, usando o provisório: %s", pasta, erro)
        return None

    def _ajustar_tamanho(self, img):
        # Deixa o PNG mais ou menos da altura do provisório, sempre com fator inteiro
        alvo = pixelart.ALTURA * self.escala
        if img.height() < alvo:
            return img.zoom(max(1, round(alvo / img.height())))
        if img.height() > alvo * 2:
            return img.subsample(round(img.height() / alvo))
        return img
