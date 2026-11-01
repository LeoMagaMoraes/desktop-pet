"""Some quando um programa abre em tela cheia no monitor dele (jogo, filme,
apresentação) e volta quando sai. Lembrete tocando faz ele aparecer mesmo assim.
"""

import random
import time

from . import tela


class TelaCheia:
    def __init__(self, mascote):
        self.m = mascote
        self.d = mascote.estado.dados["rotina"]
        self.escondido = False
        self._prox = 0.0

    @property
    def ligado(self):
        return self.d["tela_cheia"]

    def alternar(self):
        self.d["tela_cheia"] = not self.d["tela_cheia"]
        self._prox = 0.0

    def tick(self):
        agora = time.time()
        if agora < self._prox:
            return
        self._prox = agora + 1
        m = self.m
        cheia = (self.ligado and m.lembretes.ativo is None and m.acao != "pendurado"
                 and tela.tela_cheia_em(m.monitor.tela))
        if cheia != self.escondido:
            self._aplicar(cheia)

    def _aplicar(self, esconder):
        m = self.m
        self.escondido = esconder
        if esconder:
            m.menu.fechar()
            m.balao.esconder()
            m.root.withdraw()
        else:
            m.root.deiconify()
            tela.estilo_ferramenta(m.root)      # o withdraw pode tirar o estilo "sem ícone na barra"
            m._pos_janela = None
            if random.random() < 0.3:
                m.falar("Voltei! 👀", 1.5)
