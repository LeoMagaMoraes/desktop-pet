"""Janelinha de Status: fase, XP, barrinhas dos status e tokens do Claude Code."""

import tkinter as tk
from tkinter import font as tkfont

from . import config, especies, necessidades, tokens

FUNDO = "#1F1E1D"
TEXTO = "#F5F0E8"
APAGADO = "#9A948C"
VAZIO = "#3A3836"
LARANJA = "#D97757"
VERDE = "#7BC67B"
AMARELO = "#F2C14E"
VERMELHO = "#E8455A"
AZUL = "#8FB4FF"
SEGMENTOS = 10


def cor_da_barra(valor):
    return VERDE if valor >= 60 else AMARELO if valor >= 30 else VERMELHO


class Painel:
    def __init__(self, mascote):
        self.m = mascote
        self.janela = None
        e = mascote.escala
        self.fonte = tkfont.Font(root=mascote.root, family="Segoe UI", size=10)
        self.fonte_titulo = tkfont.Font(root=mascote.root, family="Segoe UI", size=11, weight="bold")
        self.fonte_peq = tkfont.Font(root=mascote.root, family="Segoe UI", size=9)
        self.seg_w = 3 * e        # largura de cada quadradinho da barra
        self.seg_h = 2 * e
        self.linha_h = 5 * e
        # Rótulo + barra + número, medidos com a fonte de verdade
        rotulo = self.fonte.measure("😊 Felicidade")
        self.largura = 8 * e + rotulo + 3 * e + SEGMENTOS * self.seg_w + self.fonte.measure("100") + 3 * e

    @property
    def aberto(self):
        return self.janela is not None

    def abrir(self):
        if self.aberto:
            self.janela.lift()
            return
        j = self.janela = tk.Toplevel(self.m.root)
        j.title(f"Status do {especies.especie(self.m.especie).nome}")
        j.attributes("-toolwindow", True)
        j.attributes("-topmost", True)
        j.resizable(False, False)
        j.config(bg=FUNDO)
        j.protocol("WM_DELETE_WINDOW", self.fechar)
        j.bind("<Escape>", lambda e: self.fechar())
        self.canvas = tk.Canvas(j, width=self.largura, height=10, bg=FUNDO, highlightthickness=0)
        self.canvas.pack(padx=0, pady=0)
        self._desenhar()
        self._posicionar()
        self._loop()

    def fechar(self):
        if self.janela is not None:
            self.janela.destroy()
            self.janela = None

    def _loop(self):
        # Atualiza a cada segundo enquanto estiver aberto
        if self.janela is None:
            return
        self._desenhar()
        self.janela.after(1000, self._loop)

    def _posicionar(self):
        j = self.janela
        j.update_idletasks()
        w, h = j.winfo_width(), j.winfo_height()
        area = self.m.area
        x = round(min(max(self.m.corpo.x - w / 2, area.esquerda), area.direita - w))
        y = round(max(area.topo, self.m.corpo.y - self.m.sprites.altura_corpo - h - 60))
        j.geometry(f"+{x}+{y}")

    def _desenhar(self):
        c = self.canvas
        c.delete("all")
        e = self.m.escala
        d = self.m.estado.dados
        s = d["status"]
        pad = 4 * e
        y = pad

        # Fase e XP
        fase = self.m.fase
        c.create_text(pad, y, anchor="nw", fill=TEXTO, font=self.fonte_titulo,
                      text=f"{especies.nome_fase(self.m.especie, fase)}  ·  ⭐ {d['xp']} XP")
        y += self.linha_h + e
        proxima = necessidades.proxima_fase(d["xp"])
        if proxima:
            nome, alvo = proxima
            inicio = necessidades.xp_minimo(fase)
            fracao = (d["xp"] - inicio) / max(1, alvo - inicio)
            self._barra(pad, y, self.largura - 2 * pad, fracao, LARANJA)
            y += self.seg_h + e
            c.create_text(pad, y, anchor="nw", fill=APAGADO, font=self.fonte_peq,
                          text=f"Faltam {alvo - d['xp']} XP pra virar {especies.nome_fase(self.m.especie, nome)}")
        else:
            c.create_text(pad, y, anchor="nw", fill=APAGADO, font=self.fonte_peq, text="Fase máxima! 👑")
        y += self.linha_h + 2 * e

        # Barrinhas dos status
        linhas = (("🍖 Fome", s["fome"]), ("💤 Energia", s["energia"]),
                  ("😊 Felicidade", s["felicidade"]), ("🛁 Limpeza", 100 - d["sujeira"]))
        # A barra começa depois do rótulo mais comprido
        x_barra = pad + max(self.fonte.measure(r) for r, _ in linhas) + 3 * e
        for rotulo, valor in linhas:
            c.create_text(pad, y + self.seg_h / 2, anchor="w", fill=TEXTO, font=self.fonte, text=rotulo)
            self._segmentos(x_barra, y, valor)
            c.create_text(self.largura - pad, y + self.seg_h / 2, anchor="e", fill=APAGADO,
                          font=self.fonte, text=f"{round(valor)}")
            y += self.linha_h

        saude = "🤒 Gripado: dá Remédio no menu" if d["doente"] else "❤ Saudável"
        c.create_text(pad, y, anchor="nw", fill=VERMELHO if d["doente"] else TEXTO,
                      font=self.fonte, text=saude)
        y += self.linha_h

        # Avisos de modo
        notas = []
        if not d["modo_tamagotchi"]:
            notas.append("Modo Tamagotchi desligado: status pausados")
        elif fase == "ovo":
            notas.append("Ovos não sentem fome. Faz carinho pra chocar!")
        for nota in notas:
            c.create_text(pad, y, anchor="nw", fill=APAGADO, font=self.fonte_peq, text=nota,
                          width=self.largura - 2 * pad)
            y += self.linha_h

        y = self._desenhar_tokens(c, y + e, pad)
        c.config(height=y + pad // 2)

    def _texto(self, x, y, texto, cor=TEXTO, fonte=None, anchor="nw"):
        """Escreve e devolve a altura usada (quebra a linha se não couber)."""
        item = self.canvas.create_text(x, y, anchor=anchor, fill=cor, font=fonte or self.fonte, text=texto,
                                       width=self.largura - 2 * x if anchor == "nw" else 0)
        x0, y0, x1, y1 = self.canvas.bbox(item)
        return y1 - y0

    def _desenhar_tokens(self, c, y, pad):
        """Tokens da sessão e da semana, com a meta. Uso deste PC, não o limite do plano."""
        e = self.m.escala
        cc = self.m.cc
        c.create_line(pad, y, self.largura - pad, y, fill=VAZIO, width=max(1, e // 2))
        y += 2 * e
        y += self._texto(pad, y, "🤖 Claude Code · este PC", fonte=self.fonte_titulo) + e

        semana = cc.contar(cc.semana) if cc.semana is not None else None
        sessao = cc.contar(cc.sessao)
        meta = cc.meta()
        largura_barra = self.largura - 2 * pad

        # Últimos 7 dias, comparado com a meta
        c.create_text(pad, y, anchor="nw", fill=TEXTO, font=self.fonte, text="Últimos 7 dias")
        if semana is None:
            valor = "contando..."
        else:
            valor = tokens.formatar(semana) + (f" / {tokens.formatar(meta)}" if meta else "")
        c.create_text(self.largura - pad, y, anchor="ne", fill=APAGADO, font=self.fonte, text=valor)
        y += self.linha_h + e // 2
        fracao = (semana or 0) / meta if meta else 0
        cor = LARANJA if fracao < 0.8 else AMARELO if fracao < 1 else VERMELHO
        self._barra(pad, y, largura_barra, fracao, cor)
        y += self.seg_h + 2 * e

        # Sessão atual, como parte da semana
        c.create_text(pad, y, anchor="nw", fill=TEXTO, font=self.fonte, text="Sessão atual")
        c.create_text(self.largura - pad, y, anchor="ne", fill=APAGADO, font=self.fonte,
                      text=tokens.formatar(sessao) if cc.sessao else "—")
        y += self.linha_h + e // 2
        self._barra(pad, y, largura_barra, sessao / semana if semana else 0, AZUL)
        y += self.seg_h + 2 * e

        if cc.ultima_task:
            y += self._texto(pad, y, f"Última task: {tokens.formatar(cc.contar(cc.ultima_task))} tokens")
        if cc.semana:
            s = cc.semana
            cache = s["cache_criacao"] + s["cache_leitura"]
            y += self._texto(pad, y, f"Semana: entrada {tokens.formatar(s['entrada'])} · "
                                     f"saída {tokens.formatar(s['saida'])} · cache {tokens.formatar(cache)}",
                             APAGADO, self.fonte_peq)

        if fracao >= 1:
            y += self._texto(pad, y, "🛌 Passou da meta da semana", VERMELHO, self.fonte_peq)
        elif fracao >= config.META_EMPANTURRADO:
            y += self._texto(pad, y, "😪 Perto da meta: ele fica empanturrado", AMARELO, self.fonte_peq)

        modo = "só input + output" if cc.so_io else "tudo, com cache"
        y += e + self._texto(pad, y + e, f"Contando: {modo} (troca no menu Claude Code).\n"
                                         "É o uso deste PC nos últimos 7 dias, não o limite do "
                                         "seu plano: esse aparece no /usage.", APAGADO, self.fonte_peq)
        return y

    def _segmentos(self, x, y, valor):
        """Barra em quadradinhos, estilo pixel."""
        cheios = round(valor / 100 * SEGMENTOS)
        cor = cor_da_barra(valor)
        for i in range(SEGMENTOS):
            x0 = x + i * self.seg_w
            self.canvas.create_rectangle(x0, y, x0 + self.seg_w - 2, y + self.seg_h,
                                         fill=cor if i < cheios else VAZIO, width=0)

    def _barra(self, x, y, largura, fracao, cor):
        self.canvas.create_rectangle(x, y, x + largura, y + self.seg_h, fill=VAZIO, width=0)
        self.canvas.create_rectangle(x, y, x + largura * max(0.0, min(1.0, fracao)), y + self.seg_h,
                                     fill=cor, width=0)
