"""Menu do clique direito: janelinha escura com ícones em pixel art, barrinhas dos
status e chaves liga/desliga. Os submenus (Monitor, Claude Code) abrem como
páginas dentro do próprio menu, com um "Voltar" no topo.

Fecha com Esc, clicando fora ou escolhendo uma opção.
"""

import tkinter as tk
from tkinter import font as tkfont

from . import especies, lembretes, loja, necessidades, pixelart, tela, tokens
from .sprites import grade_para_imagem

FUNDO = "#262422"
BORDA = "#45403B"
DESTAQUE = "#3A3532"
TEXTO = "#F5F0E8"
APAGADO = "#9A948C"
SECAO = "#B8A99A"
LARANJA = "#D97757"
VERMELHO = "#E8455A"
VERDE = "#7BC67B"
AMARELO = "#F2C14E"
VAZIO = "#45403B"


def cor_do_valor(valor):
    return VERDE if valor >= 60 else AMARELO if valor >= 30 else VERMELHO


class MenuClawd:
    def __init__(self, mascote):
        self.m = mascote
        e = mascote.escala
        self.e = e
        self.janela = None
        self.pagina = "principal"
        self._ancora = (0, 0)
        self._liberou_botao = False      # só fecha clicando fora depois de soltar o clique que abriu
        self._vigia = None               # id do after que confere os cliques
        root = mascote.root
        self.fonte = tkfont.Font(root=root, family="Segoe UI", size=10)
        self.fonte_negrito = tkfont.Font(root=root, family="Segoe UI", size=10, weight="bold")
        self.fonte_titulo = tkfont.Font(root=root, family="Segoe UI", size=11, weight="bold")
        self.fonte_pequena = tkfont.Font(root=root, family="Segoe UI", size=8)
        self.fonte_secao = tkfont.Font(root=root, family="Segoe UI", size=8, weight="bold")
        escala_icone = max(2, e - 2)
        self.icones = {nome: grade_para_imagem(root, g, escala_icone) for nome, g in pixelart.ICONES.items()}
        self.largura = 64 * e
        self._retratos = {}              # miniatura de cada bicho em cada fase

    # ------------------------------------------------------------------ abrir e fechar

    @property
    def aberto(self):
        return self.janela is not None

    def abrir(self, x, y):
        self.fechar()
        self.pagina = "principal"
        self._ancora = (x, y)
        j = self.janela = tk.Toplevel(self.m.root)
        j.withdraw()
        j.overrideredirect(True)
        j.attributes("-topmost", True)
        j.config(bg=BORDA)
        j.bind("<Escape>", lambda ev: self.fechar())
        j.bind("<BackSpace>", lambda ev: self._ir("principal"))
        self._liberou_botao = False
        self._montar()
        j.deiconify()
        tela.cantos_arredondados(j)
        j.focus_force()
        self._vigiar_cliques()

    def fechar(self):
        if self._vigia is not None:
            self.m.root.after_cancel(self._vigia)
            self._vigia = None
        if self.janela is not None:
            self.janela.destroy()
            self.janela = None

    def _vigiar_cliques(self):
        """Fecha quando você clica em qualquer lugar fora do menu."""
        self._vigia = None
        if self.janela is None:
            return
        apertado = tela.botao_do_mouse_apertado()
        if not apertado:
            self._liberou_botao = True
        elif self._liberou_botao:
            px, py = self.janela.winfo_pointerxy()
            x0, y0 = self.janela.winfo_rootx(), self.janela.winfo_rooty()
            dentro = x0 <= px < x0 + self.janela.winfo_width() and y0 <= py < y0 + self.janela.winfo_height()
            if not dentro:
                self.fechar()
                return
        self._vigia = self.m.root.after(60, self._vigiar_cliques)

    def _ir(self, pagina):
        if self.janela is not None:
            self.pagina = pagina
            self._montar()

    # ------------------------------------------------------------------ montagem

    def _montar(self):
        j = self.janela
        for filho in j.winfo_children():
            filho.destroy()
        e = self.e
        self.corpo = tk.Frame(j, bg=FUNDO, padx=e, pady=e)
        self.corpo.pack(padx=1, pady=1, fill="both")
        tk.Frame(self.corpo, width=self.largura, height=0, bg=FUNDO).pack()   # largura mínima
        {"principal": self._pagina_principal, "monitor": self._pagina_monitor,
         "claude": self._pagina_claude, "clima": self._pagina_clima,
         "pets": self._pagina_pets, "lembretes": self._pagina_lembretes, "loja": self._pagina_loja,
         "rotina": self._pagina_rotina}[self.pagina]()
        self._posicionar()

    def _posicionar(self):
        """Abre acima e à esquerda do mouse (o Clawd mora lá embaixo), sem sair da tela."""
        j = self.janela
        j.update_idletasks()
        w, h = j.winfo_reqwidth(), j.winfo_reqheight()
        area = self.m.area
        x, y = self._ancora
        x = min(max(x - w + 4 * self.e, area.esquerda + 4), area.direita - w - 4)
        y = y - h - 2 * self.e if y - h - 2 * self.e >= area.topo else min(y + 2 * self.e, area.base - h)
        j.geometry(f"{w}x{h}+{round(x)}+{round(max(area.topo, y))}")

    def _pagina_principal(self):
        m = self.m
        self._cabecalho()
        ativo = m.tama.ativo
        s = m.estado.status

        tocando = m.lembretes.ativo
        if tocando:
            # Lembrete tocando: as respostas dele vêm primeiro
            self._secao("⏰ " + tocando["texto"][:40])
            self._item("relogio", "Feito!", m.lembretes.dispensar, destaque_cor="#2E4A2E")
            self._item("relogio", f"Me lembra em {lembretes.ADIAR_MINUTOS} min", m.lembretes.adiar)

        self._secao("CUIDAR")
        barra = (lambda v: (lambda pai: self._mini_barra(pai, v))) if ativo else (lambda v: None)
        self._item("comida", "Alimentar", m.alimentar, direita=barra(s["fome"]))
        self._item("bola", "Brincar", m.brincar, direita=barra(s["felicidade"]))
        if m.acao == "dormindo":
            self._item("sol", "Acordar", lambda: m.acordar("Bom dia! ☀️"))
        else:
            self._item("lua", "Dormir", m.dormir, direita=barra(s["energia"]))
        if ativo and m.estado.dados["doente"]:
            self._item("pilula", "Dar remédio", m.dar_remedio, destaque_cor=VERMELHO,
                       direita=lambda pai: self._etiqueta(pai, "gripado", VERMELHO))

        self._secao("VER")
        self._item("grafico", "Status e tokens", m.mostrar_status)
        temperatura = m.clima.rotulo()
        self._item("nuvem", "Clima", m.mostrar_clima,
                   direita=(lambda pai: self._etiqueta(pai, temperatura, TEXTO)) if temperatura else None)
        n_lembretes = len(m.lembretes.lista)
        self._item("relogio", "Lembretes", lambda: self._ir("lembretes"), fecha=False,
                   direita=lambda pai: self._etiqueta(pai, f"{n_lembretes or 'nenhum'}  ›"))
        self._item("lista", "Resumo do dia", m.resumo.mostrar)
        saldo = m.loja.saldo()
        self._item("sacola", "Loja", lambda: self._ir("loja"), fecha=False,
                   direita=lambda pai: self._etiqueta(pai, f"⭐ {saldo} XP  ›"))

        self._secao("AJUSTES")
        n = len(m.monitores)
        self._item("monitor", "Monitor", lambda: self._ir("monitor"), fecha=False,
                   direita=lambda pai: self._etiqueta(pai, f"{n} ligado{'s' if n > 1 else ''}  ›"))
        self._chave("janela", "Andar nas janelas", m.janelas.ligado, m.janelas.alternar)
        self._item("clawd", "Claude Code", lambda: self._ir("claude"), fecha=False,
                   direita=lambda pai: self._etiqueta(pai, "›"))
        cidade = m.clima.d.get("nome_exibido") or m.clima.d.get("cidade") or ""
        self._item("sol", "Clima e cidade", lambda: self._ir("clima"), fecha=False,
                   direita=lambda pai: self._etiqueta(pai, f"{cidade}  ›"))
        self._item("lua", "Rotina e datas", lambda: self._ir("rotina"), fecha=False,
                   direita=lambda pai: self._etiqueta(pai, "›"))
        esp = especies.especie(m.especie)
        self._item(esp.icone, "Trocar de pet", lambda: self._ir("pets"), fecha=False,
                   direita=lambda pai: self._etiqueta(pai, f"{esp.nome}  ›"))
        ligado = m.estado.dados["modo_tamagotchi"]
        self._chave("ovo", "Modo Tamagotchi", ligado, lambda: m.tama.mudar_modo(not ligado))

        self._separador()
        self._item("porta", "Sair", m.sair, destaque_cor="#5A2E2E")

    def _pagina_monitor(self):
        self._voltar("Monitor")
        atual = self.m.monitor.nome
        for mon in self.m.monitores:
            marcado = mon.nome == atual
            self._item("monitor", mon.rotulo, (lambda nome=mon.nome: self.m.trocar_monitor(nome)),
                       negrito=marcado,
                       direita=(lambda pai: self._etiqueta(pai, "● aqui", LARANJA)) if marcado else None)
        if len(self.m.monitores) == 1:
            self._nota("Só tem um monitor ligado. Plugue outro e ele aparece aqui.")
        else:
            self._nota("Dica: arrastar e soltar ele em outra tela também muda de monitor.")

    def _pagina_claude(self):
        m = self.m
        cc = m.cc
        d = m.estado.dados["claude"]
        self._voltar("Claude Code")
        self._chave("moeda", "Contar só input e output", cc.so_io, lambda: cc.alternar_so_io(not cc.so_io))
        meta = cc.meta()
        self._item("alvo", "Meta semanal", m._perguntar_meta,
                   direita=lambda pai: self._etiqueta(pai, tokens.formatar(meta) if meta else "sem meta"))
        self._chave("som", "Sons", d["sons"], lambda: d.__setitem__("sons", not d["sons"]))
        if m.fiscal.tem_git:
            self._chave("lista", "Fiscal do git", m.fiscal.ligado, m.fiscal.alternar)
        self._item("plugue", "Reinstalar hooks", m._reinstalar_hooks)

        semana = tokens.formatar(cc.contar(cc.semana)) if cc.semana is not None else "contando..."
        sessao = tokens.formatar(cc.contar(cc.sessao)) if cc.sessao else "—"
        self._nota(f"Últimos 7 dias: {semana}  ·  sessão: {sessao}\n"
                   "Uso deste PC, não o limite do plano (veja /usage).")

    def _pagina_pets(self):
        """Um item por bicho, com a miniatura dele na fase em que está."""
        m = self.m
        self._voltar("Trocar de pet")
        for esp in especies.ESPECIES.values():
            resumo = especies.resumo_do_pet(m.estado.dados, esp.id)
            fase, xp = resumo if resumo else ("ovo", 0)
            agora = esp.id == m.especie
            if agora:
                legenda, cor = "● agora", LARANJA
            elif resumo:
                legenda, cor = f"{especies.nome_fase(esp.id, fase)} · {xp} XP", APAGADO
            else:
                legenda, cor = "novo! 🥚", VERDE
            self._linha(None, f"{esp.nome} {esp.emoji}", lambda novo=esp.id: self._escolher_pet(novo),
                        negrito=agora, imagem=self._retrato(esp.id, fase),
                        direita=lambda pai, t=legenda, c=cor: self._etiqueta(pai, t, c))
        self._nota("Cada pet tem o próprio XP e as próprias necessidades. Quem não está na tela "
                   "fica guardado, pausado, até você trocar de volta.")

    def _pagina_lembretes(self):
        """Novo lembrete + os próximos, em ordem; clicar num deles apaga."""
        m = self.m
        self._voltar("Lembretes")
        self._item("relogio", "Novo lembrete", m.dialogo_lembrete.abrir, negrito=True)
        proximos = m.lembretes.proximos()
        if proximos:
            self._secao("PRÓXIMOS  ·  clique pra apagar")
        for l in proximos:
            quando = lembretes.formatar(lembretes.quando_de(l), repetir=l.get("repetir"))
            texto = l["texto"] if len(l["texto"]) <= 28 else l["texto"][:27] + "…"
            self._linha("relogio", texto, lambda ident=l["id"]: self._apagar_lembrete(ident),
                        destaque_cor="#5A2E2E",
                        direita=lambda pai, q=quando: self._etiqueta(pai, q))
        if not proximos:
            self._nota("Nenhum lembrete marcado. Ele te avisa acenando, com um balão e um alarminho; "
                       "clique nele pra dizer que viu.")

    def _pagina_loja(self):
        """Um item por acessório, com o pet usando ele na miniatura."""
        m = self.m
        lj = m.loja
        self._voltar("Loja")
        saldo = lj.saldo()
        fase = "filhote" if m.fase == "ovo" else m.fase           # ovo não se veste: mostra o filhote
        for item in loja.ITENS.values():
            if lj.usando(item.id):
                legenda, cor = "✓ usando", LARANJA
            elif lj.comprado(item.id):
                legenda, cor = "usar", TEXTO
            else:
                legenda, cor = f"⭐ {item.preco} XP", VERDE if saldo >= item.preco else APAGADO
            self._linha(None, f"{item.nome} {item.emoji}", lambda i=item.id: self._escolher_item(i),
                        negrito=lj.usando(item.id), imagem=self._retrato(m.especie, fase, frozenset({item.id})),
                        direita=lambda pai, t=legenda, c=cor: self._etiqueta(pai, t, c))
        nota = f"Saldo: ⭐ {saldo} XP. Comprar não tira a evolução. Clique de novo pra tirar."
        if m.fase == "ovo":
            nota += " Ovo não se veste: ele usa quando nascer."
        self._nota(nota)

    def _escolher_item(self, ident):
        self.m.falar(self.m.loja.escolher(ident), 2.5)
        self._montar()

    def _pagina_rotina(self):
        m = self.m
        self._voltar("Rotina e datas")
        hora = m.hora_dormir.hora
        self._item("lua", "Hora de dormir", m._perguntar_hora_dormir,
                   direita=lambda pai: self._etiqueta(pai, hora or "desligada"))
        aniversario = m.estado.dados["rotina"].get("aniversario")
        self._item("bolo", "Seu aniversário", m._perguntar_aniversario,
                   direita=lambda pai: self._etiqueta(pai, aniversario or "—"))
        self._chave("monitor", "Sumir em tela cheia", m.tela_cheia.ligado, m.tela_cheia.alternar)
        self._chave("som", "Dançar com música", m.musica.ligado, m.musica.alternar)
        self._chave("lista", "Resumo do dia às 18h", m.resumo.automatico, m.resumo.alternar_automatico)
        hoje = m.datas.atual
        if hoje:
            self._nota(f"Hoje é dia de festa: {hoje.nome}! 🎉")
        else:
            self._nota("Ele comemora Natal, Ano Novo, Carnaval, Páscoa, Halloween, Dia do Programador "
                       "e o seu aniversário.")

    def _apagar_lembrete(self, ident):
        self.m.lembretes.apagar(ident)
        self._montar()

    def _escolher_pet(self, novo):
        self.fechar()
        if novo != self.m.especie:
            self.m.root.after(10, lambda: self.m.trocar_pet(novo))

    def _pagina_clima(self):
        m = self.m
        cl = m.clima
        d = cl.d
        self._voltar("Clima")
        cidade = d.get("nome_exibido") or d.get("cidade") or "?"
        estado = d.get("estado") or ""
        self._item("nuvem", "Ver o tempo agora", m.mostrar_clima,
                   direita=lambda pai: self._etiqueta(pai, cl.rotulo(), TEXTO))
        self._item("alvo", "Trocar cidade", m._perguntar_cidade,
                   direita=lambda pai: self._etiqueta(pai, cidade))
        self._item("plugue", "Atualizar agora", cl.atualizar_agora)
        quando = (d.get("atualizado") or "")[11:16]
        nota = f"{cidade}{', ' + estado if estado else ''}"
        nota += f" · atualizado às {quando}" if quando else " · ainda buscando..."
        if cl.erro:
            nota += "\nSem internet agora: usando o último clima."
        self._nota(nota + "\nDados do Open-Meteo, a cada 30 minutos.")

    # ------------------------------------------------------------------ peças

    def _cabecalho(self):
        """Miniatura do Clawd, nome da fase, XP e a barra até a próxima fase."""
        m, e = self.m, self.e
        d = m.estado.dados
        topo = tk.Frame(self.corpo, bg=FUNDO, padx=e, pady=e)
        topo.pack(fill="x")
        tk.Label(topo, image=self._retrato(m.especie, m.fase, m.roupas), bg=FUNDO).pack(side="left", padx=(0, 2 * e))
        textos = tk.Frame(topo, bg=FUNDO)
        textos.pack(side="left", fill="x", expand=True)
        tk.Label(textos, text=especies.nome_fase(m.especie, m.fase), font=self.fonte_titulo, fg=TEXTO,
                 bg=FUNDO, anchor="w").pack(fill="x")
        proxima = necessidades.proxima_fase(d["xp"])
        if proxima:
            nome, alvo = proxima
            inicio = necessidades.xp_minimo(m.fase)
            fracao = (d["xp"] - inicio) / max(1, alvo - inicio)
            legenda = f"⭐ {d['xp']} XP  ·  {alvo - d['xp']} pra {especies.nome_fase(m.especie, nome)}"
        else:
            fracao, legenda = 1.0, f"⭐ {d['xp']} XP  ·  fase máxima!"
        tk.Label(textos, text=legenda, font=self.fonte_pequena, fg=APAGADO, bg=FUNDO,
                 anchor="w").pack(fill="x")
        barra = tk.Canvas(textos, width=1, height=e, bg=VAZIO, highlightthickness=0, bd=0)
        barra.pack(fill="x", pady=(e // 2, 0))
        barra.bind("<Configure>", lambda ev: (barra.delete("all"), barra.create_rectangle(
            0, 0, ev.width * min(1.0, fracao), ev.height, fill=LARANJA, width=0)))
        if not m.estado.dados["modo_tamagotchi"]:
            self._nota("Modo Tamagotchi desligado: status pausados.")
        self._separador()

    def _retrato(self, especie, fase, roupas=frozenset()):
        """Miniatura do bicho parado na fase dele (cabeçalho, pets e loja)."""
        chave = (especie, fase, roupas)
        if chave not in self._retratos:
            grade = pixelart.animacoes(fase, roupas, especie)["parado"][1][0]
            self._retratos[chave] = grade_para_imagem(self.m.root, grade, max(2, self.e // 2))
        return self._retratos[chave]

    def _secao(self, texto):
        tk.Label(self.corpo, text=texto, font=self.fonte_secao, fg=SECAO, bg=FUNDO, anchor="w",
                 padx=2 * self.e).pack(fill="x", pady=(self.e, 0))

    def _separador(self):
        tk.Frame(self.corpo, height=1, bg=BORDA).pack(fill="x", pady=self.e, padx=self.e)

    def _nota(self, texto):
        tk.Label(self.corpo, text=texto, font=self.fonte_pequena, fg=APAGADO, bg=FUNDO, anchor="w",
                 justify="left", wraplength=self.largura - 4 * self.e, padx=2 * self.e,
                 pady=self.e // 2).pack(fill="x")

    def _etiqueta(self, pai, texto, cor=APAGADO):
        return tk.Label(pai, text=texto, font=self.fonte_pequena, fg=cor, bg=pai["bg"])

    def _mini_barra(self, pai, valor):
        """Cinco quadradinhos + o número, do lado direito do item."""
        e = self.e
        quadro = tk.Frame(pai, bg=pai["bg"])
        c = tk.Canvas(quadro, width=5 * (e + 2), height=e + 2, bg=pai["bg"], highlightthickness=0, bd=0)
        cheios = round(valor / 20)
        for i in range(5):
            x = i * (e + 2)
            c.create_rectangle(x, 1, x + e, e + 1, width=0, fill=cor_do_valor(valor) if i < cheios else VAZIO)
        c.pack(side="left")
        tk.Label(quadro, text=f"{round(valor):>3}", font=self.fonte_pequena, fg=APAGADO, bg=pai["bg"],
                 width=3, anchor="e").pack(side="left")
        return quadro

    def _linha(self, icone, texto, ao_clicar, negrito=False, destaque_cor=DESTAQUE, direita=None, imagem=None):
        """Uma linha clicável com ícone (ou outra imagem), texto e algo opcional na direita."""
        e = self.e
        linha = tk.Frame(self.corpo, bg=FUNDO, padx=2 * e, pady=e, cursor="hand2")
        linha.pack(fill="x")
        tk.Label(linha, image=imagem or self.icones[icone], bg=FUNDO,
                 width=imagem.width() if imagem else 6 * e).pack(side="left")
        tk.Label(linha, text=texto, font=self.fonte_negrito if negrito else self.fonte, fg=TEXTO,
                 bg=FUNDO, anchor="w", padx=2 * e).pack(side="left", fill="x", expand=True)
        if direita is not None:
            direita(linha).pack(side="right")
        self._interativo(linha, ao_clicar, destaque_cor)
        return linha

    def _item(self, icone, texto, acao, fecha=True, negrito=False, destaque_cor=DESTAQUE, direita=None):
        def clicar():
            if fecha:
                self.fechar()
                self.m.root.after(10, acao)     # depois de fechar, pra ação poder abrir janelas
            else:
                acao()
        return self._linha(icone, texto, clicar, negrito, destaque_cor, direita)

    def _chave(self, icone, texto, ligado, alternar):
        """Item com uma chavinha liga/desliga; o menu continua aberto e se redesenha."""
        def clicar():
            alternar()
            self._montar()
        return self._linha(icone, texto, clicar, direita=lambda pai: self._desenhar_chave(pai, ligado))

    def _desenhar_chave(self, pai, ligado):
        e = self.e
        w, h = 7 * e, 4 * e
        c = tk.Canvas(pai, width=w, height=h, bg=pai["bg"], highlightthickness=0, bd=0)
        fundo = LARANJA if ligado else VAZIO
        r = h // 2
        c.create_oval(0, 0, h, h, fill=fundo, width=0)
        c.create_oval(w - h, 0, w, h, fill=fundo, width=0)
        c.create_rectangle(r, 0, w - r, h, fill=fundo, width=0)
        bola = w - h + 2 if ligado else 2
        c.create_oval(bola, 2, bola + h - 4, h - 2, fill=TEXTO, width=0)
        return c

    def _voltar(self, titulo):
        e = self.e
        topo = tk.Frame(self.corpo, bg=FUNDO, padx=2 * e, pady=e)
        topo.pack(fill="x")
        voltar = tk.Label(topo, text="‹ Voltar", font=self.fonte, fg=LARANJA, bg=FUNDO, cursor="hand2")
        voltar.pack(side="left")
        voltar.bind("<Button-1>", lambda ev: self._ir("principal"))
        tk.Label(topo, text=titulo, font=self.fonte_titulo, fg=TEXTO, bg=FUNDO).pack(side="right")
        self._separador()

    def _interativo(self, linha, ao_clicar, destaque_cor):
        """Destaca a linha inteira com o mouse em cima e chama ao_clicar no clique."""
        widgets = [linha] + list(linha.winfo_children())
        widgets += [neto for filho in linha.winfo_children() for neto in filho.winfo_children()]

        def pintar(cor):
            for w in widgets:
                try:
                    if isinstance(w, (tk.Frame, tk.Label)) or (isinstance(w, tk.Canvas) and w["bg"] in (FUNDO, DESTAQUE, destaque_cor)):
                        w.config(bg=cor)
                except tk.TclError:
                    pass

        def saiu(ev):
            # Só apaga o destaque se o mouse saiu da linha mesmo (não só pra um filho dela)
            dentro = linha.winfo_containing(ev.x_root, ev.y_root)
            if dentro not in widgets:
                pintar(FUNDO)

        for w in widgets:
            w.bind("<Enter>", lambda ev: pintar(destaque_cor))
            w.bind("<Leave>", saiu)
            w.bind("<ButtonRelease-1>", lambda ev: ao_clicar())
