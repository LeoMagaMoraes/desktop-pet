"""O mascote: janela transparente, máquina de ações, física e interação com o mouse."""

import logging
import random
import signal
import time
import tkinter as tk

from . import config, fisica, interacao, necessidades, tela
from .balao import Balao
from .efeitos import Efeitos
from .estado import Estado
from .painel import Painel
from .sprites import BibliotecaSprites, criar_imagens_efeito
from .tamagotchi import Tamagotchi

log = logging.getLogger(__name__)

FALAS_POUSO = ["Ufa!", "Pousei!", "De novo! De novo!", "Wheee!", "Tô inteiro!"]
FALAS_CARINHO = ["Hehe ♥", "Gostei!", "Mais!", "♥"]


class Mascote:
    def __init__(self, demo=False, arquivo_estado=config.ARQUIVO_ESTADO, fase_demo=None):
        tela.ativar_dpi()   # precisa vir antes de criar o Tk
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Clawd")
        self.root.report_callback_exception = self._erro_em_callback

        self.demo = demo
        self.escala = config.escala_para_dpi(self.root.winfo_fpixels("1i"))
        self.k = self.escala / 4        # multiplica velocidades pensadas pra escala 4
        self.estado = Estado.carregar(arquivo_estado)

        # Fase de evolução: a do save, corrigida se o XP não bater
        fase = self.estado.dados.get("fase")
        if fase not in necessidades.ORDEM_FASE:
            fase = necessidades.fase_por_xp(self.estado.dados["xp"])
        self.fase = fase_demo or fase
        self._fase_pendente = None      # fase que vem depois de chocar
        self._bibliotecas = {}
        self.sprites = self._biblioteca(self.fase)
        self.imagens_efeito = criar_imagens_efeito(self.root, self.escala)
        self.monitores = tela.monitores(self.root)
        self.monitor = self._monitor_inicial()
        self.area = self.monitor.area
        self.params = fisica.Parametros(
            gravidade=config.GRAVIDADE * self.k, quique_parede=config.QUIQUE_PAREDE,
            quique_chao=config.QUIQUE_CHAO, atrito_chao=config.ATRITO_CHAO * self.k,
            vel_min_quique=config.VEL_MIN_QUIQUE * self.k, vel_parar=20 * self.k,
            vel_max=config.VEL_MAX * self.k)

        self._montar_janela()
        self.balao = Balao(self.root, config.COR_CHAVE, self.escala)
        self.menu = self._criar_menu()

        # Posição e movimento
        self.corpo = fisica.Corpo(*self._posicao_inicial())
        self.direcao = random.choice((-1, 1))     # 1 = direita, -1 = esquerda
        self.salto = 0.0                           # altura do pulinho de comemoração
        self.salto_v = 0.0

        # Ação atual (parado, andando, comendo...) e até quando dura
        self.acao = "parado"
        self.acao_ate = None
        self.anim_inicio = time.perf_counter()

        # Mouse
        self.apertado_em = None       # (x, y) onde o botão foi apertado
        self.arrastando = False
        self.pegada = (0.0, 0.0)      # distância do mouse ao ponto (x, y) do Clawd
        self.amostras = []            # [(t, x, y)] do arrasto, pra calcular o arremesso
        self.detector = interacao.DetectorSacudida(
            config.SACUDIDA_REVERSOES, config.SACUDIDA_JANELA, config.SACUDIDA_AMPLITUDE * self.k)
        self.tonto_pendente = False
        self.arremessado = False

        self._prox_particula = 0.0
        self._ultimo_ai = 0.0
        self._img_atual = None
        self._pos_janela = None
        self._ultimo_tick = time.perf_counter()

        # Necessidades, avisos e XP (precisa do save ainda sem o horário novo)
        self.tama = Tamagotchi(self)
        self.painel = Painel(self)

    # ------------------------------------------------------------------ montagem

    def _montar_janela(self):
        e = self.escala
        self.larg_janela = self.sprites.largura_max + 2 * config.MARGEM_LATERAL * e
        self.alt_janela = self.sprites.altura_max + config.MARGEM_TOPO * e
        r = self.root
        r.overrideredirect(True)                         # sem borda
        r.attributes("-topmost", True)                   # sempre por cima
        r.attributes("-transparentcolor", config.COR_CHAVE)
        r.config(bg=config.COR_CHAVE)
        self.canvas = tk.Canvas(r, width=self.larg_janela, height=self.alt_janela,
                                bg=config.COR_CHAVE, highlightthickness=0, bd=0, cursor="hand2")
        self.canvas.pack()
        # Âncora "s": os pés ficam no meio da borda de baixo da janela
        self.item_sprite = self.canvas.create_image(self.larg_janela / 2, self.alt_janela, anchor="s")
        self.efeitos = Efeitos(self.canvas, self.imagens_efeito, self.item_sprite, self.k)

        self.canvas.bind("<ButtonPress-1>", self._apertou)
        self.canvas.bind("<B1-Motion>", self._moveu)
        self.canvas.bind("<ButtonRelease-1>", self._soltou)
        self.canvas.bind("<ButtonPress-3>", self._abrir_menu)
        # Mouse passando por cima sem apertar = esfregar (banho)
        self.canvas.bind("<Motion>", lambda e: self.tama.esfregar(e.x_root, e.y_root))

    def _criar_menu(self):
        m = tk.Menu(self.root, tearoff=0, postcommand=self._atualizar_menu)
        m.add_command(label="🍖  Alimentar", command=self.alimentar)
        m.add_command(label="⚽  Brincar", command=self.brincar)
        m.add_command(label="💤  Dormir", command=self._dormir_ou_acordar)
        m.add_command(label="💊  Remédio", command=self.dar_remedio)
        m.add_separator()
        m.add_command(label="📊  Status", command=self.mostrar_status)
        m.add_command(label="☁️  Clima", command=self.mostrar_clima)
        # Submenu com um item por monitor (montado de novo toda vez que o menu abre)
        self.menu_monitores = tk.Menu(m, tearoff=0)
        self.var_monitor = tk.StringVar(self.root, value=self.monitor.nome)
        m.add_cascade(label="🖥  Monitor", menu=self.menu_monitores)
        m.add_separator()
        self.var_modo = tk.BooleanVar(self.root, value=self.estado.dados["modo_tamagotchi"])
        m.add_checkbutton(label="Modo Tamagotchi", variable=self.var_modo,
                          command=lambda: self.tama.mudar_modo(self.var_modo.get()))
        m.add_separator()
        m.add_command(label="Sair", command=self.sair)
        return m

    def _atualizar_menu(self):
        # Ajusta os itens toda vez que o menu abre
        dormindo = self.acao == "dormindo"
        self.menu.entryconfigure(2, label="☀️  Acordar" if dormindo else "💤  Dormir")
        doente = self.estado.dados["doente"] and self.tama.ativo
        self.menu.entryconfigure(3, state="normal" if doente else "disabled")
        self.var_modo.set(self.estado.dados["modo_tamagotchi"])

        # Relê os monitores (pode ter plugado ou tirado um) e remonta o submenu
        self.monitores = tela.monitores(self.root)
        self.menu_monitores.delete(0, "end")
        for mon in self.monitores:
            self.menu_monitores.add_radiobutton(
                label=mon.rotulo, value=mon.nome, variable=self.var_monitor,
                command=lambda nome=mon.nome: self.trocar_monitor(nome))
        self.var_monitor.set(self.monitor.nome)
        self.menu.entryconfigure(self.INDICE_MONITOR, state="normal" if len(self.monitores) > 1 else "disabled")

    INDICE_MONITOR = 7     # posição do "Monitor" no menu (separadores contam)

    def _biblioteca(self, fase):
        if fase not in self._bibliotecas:
            self._bibliotecas[fase] = BibliotecaSprites(self.root, self.escala, config.PASTA_SPRITES, fase)
        return self._bibliotecas[fase]

    def _limites(self):
        a = self.area
        return fisica.Limites(a.esquerda, a.direita, a.topo, a.base,
                              self.sprites.meia_largura, self.sprites.altura_corpo)

    def _monitor_inicial(self):
        """O monitor salvo; se não tiver, o do lugar favorito; senão o principal."""
        d = self.estado.dados
        if d.get("monitor") in {m.nome for m in self.monitores}:
            return tela.monitor_por_nome(self.monitores, d["monitor"])
        fav = d.get("lugar_favorito")
        if isinstance(fav, dict) and isinstance(fav.get("x"), (int, float)) and isinstance(fav.get("y"), (int, float)):
            return tela.monitor_no_ponto(self.monitores, fav["x"], fav["y"] - 1)
        return self.monitores[0]

    def trocar_monitor(self, nome):
        """Leva o Clawd pro outro monitor: ele cai lá do alto, no meio da tela."""
        novo = tela.monitor_por_nome(self.monitores, nome)
        if novo.nome != nome or self.acao == "pendurado":
            return
        self.monitor = novo
        self.area = novo.area
        self.estado.dados["monitor"] = novo.nome
        lim = self._limites()
        self.corpo.x = (lim.esquerda + lim.direita) / 2
        self.corpo.y = lim.topo + lim.altura
        self.corpo.vx = self.corpo.vy = 0.0
        self.corpo.no_chao = False
        self.salto = self.salto_v = 0.0
        self.arremessado = True               # pra ele comentar quando pousar
        self.mudar("caindo")
        self.falar("Mudei de monitor! 🖥️", 1.5)
        self.salvar()

    def _posicao_inicial(self):
        """Volta pro lugar favorito (onde foi solto por último), ou nasce no meio do chão."""
        lim = self._limites()
        x, y = (lim.esquerda + lim.direita) / 2, lim.chao
        fav = self.estado.dados.get("lugar_favorito")
        if isinstance(fav, dict) and isinstance(fav.get("x"), (int, float)):
            x = fav["x"]
            if isinstance(fav.get("y"), (int, float)):
                y = fav["y"]
        x = min(max(x, lim.esquerda + lim.meia_largura), lim.direita - lim.meia_largura)
        y = min(max(y, lim.topo + lim.altura), lim.chao)
        return x, y

    # ------------------------------------------------------------------ ciclo de vida

    def rodar(self):
        self.root.deiconify()
        self.root.update_idletasks()
        tela.estilo_ferramenta(self.root)
        self._desenhar(time.perf_counter())

        if self.corpo.y < self.area.base - 1:
            self.mudar("caindo")
        else:
            self.mudar("acenando", 2.5)
            self.falar(self.tama.boas_vindas() or "Oi! 👋")

        signal.signal(signal.SIGINT, lambda *_: self.root.after_idle(self.sair))
        self.root.after(config.TICK_MS, self._tick)
        self.root.after(config.TOPMOST_MS, self._manter_por_cima)
        self.root.after(config.AREA_MS, self._reler_area)
        self.root.after(config.AUTOSAVE_MS, self._autosave)
        if self.demo:
            self.root.after(1500, self._demo, 0)
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.sair()

    def sair(self):
        self.salvar()
        try:
            # Cancela os loops agendados pra não sobrar callback apontando pra janela fechada
            for pendente in self.root.tk.splitlist(self.root.tk.call("after", "info")):
                self.root.after_cancel(pendente)
            self.root.destroy()
        except tk.TclError:
            pass

    def salvar(self):
        if self.demo:
            return
        self.estado.dados["ultima_posicao"] = {"x": round(self.corpo.x), "y": round(self.corpo.y)}
        self.estado.salvar()

    def _autosave(self):
        self.salvar()
        self.root.after(config.AUTOSAVE_MS, self._autosave)

    def _manter_por_cima(self):
        # A barra de tarefas às vezes passa na frente; reforça o topmost
        for janela in (self.root, self.balao.janela):
            janela.attributes("-topmost", True)
        self.root.after(config.TOPMOST_MS, self._manter_por_cima)

    def _reler_area(self):
        # Pega monitor desligado, mudança de resolução ou da barra de tarefas
        self.monitores = tela.monitores(self.root)
        atual = tela.monitor_por_nome(self.monitores, self.monitor.nome)
        if atual.nome != self.monitor.nome:
            # O monitor dele sumiu: volta pro principal
            self.trocar_monitor(atual.nome)
        elif atual.area != self.area:
            self.monitor = atual
            self.area = nova = atual.area
            if self.acao not in ("caindo", "pendurado"):
                self.corpo.y = nova.base
                lim = self._limites()
                self.corpo.x = min(max(self.corpo.x, lim.esquerda + lim.meia_largura),
                                   lim.direita - lim.meia_largura)
        self.root.after(config.AREA_MS, self._reler_area)

    def _erro_em_callback(self, *info):
        log.error("Erro num callback do Tk", exc_info=info)

    # ------------------------------------------------------------------ ações

    def mudar(self, acao, segundos=None):
        """Troca a ação atual e reinicia a animação dela."""
        self.acao = acao
        self.acao_ate = time.perf_counter() + segundos if segundos else None
        self.anim_inicio = time.perf_counter()

    def falar(self, texto, segundos=None, fixo=False):
        self.balao.falar(texto, segundos, fixo)

    def _decidir_proxima(self):
        """O que fazer quando a ação atual acaba."""
        if self.fase == "ovo":
            self.mudar("parado", random.uniform(3, 8))    # ovo não anda
            return
        r = random.random()
        if r < 0.55:
            if random.random() < 0.4:
                self.direcao = -self.direcao
            self.mudar("andando", random.uniform(3, 9))
        elif r < 0.6:
            self.mudar("acenando", 2)
        else:
            self.mudar("parado", random.uniform(2, 6))

    def _fim_da_acao(self):
        if self.acao == "tonto":
            self.tonto_pendente = False
            self.efeitos.estrelas_girando(False)
            self.falar("Passou...", 1.5)
            self.mudar("parado", 1.5)
        elif self.acao == "chocando" and self._fase_pendente:
            self._evoluir(self._fase_pendente)
        elif self.acao == "parado":
            self._decidir_proxima()
        else:
            self.mudar("parado", random.uniform(1.5, 4))

    def _ajustar(self, nome, delta):
        """Mexe num status só quando o modo Tamagotchi está valendo."""
        if self.tama.ativo:
            self.estado.ajustar_status(nome, delta)

    def alimentar(self):
        if self.fase == "ovo":
            self.falar("Sou um ovo, ainda não como 🥚\nFaz carinho pra eu chocar!", 3)
            return
        if self.tama.ativo and self.estado.status["fome"] >= 95:
            self.falar("Tô cheio! 😋", 2)
            return
        self.mudar("comendo", 3)
        self._ajustar("fome", 25)
        self._ajustar("felicidade", 3)
        self.tama.ganhar_xp(config.XP_ALIMENTAR)
        self.falar("Nham nham! 🍤")

    def brincar(self):
        if self.fase == "ovo":
            self.mudar("comemorando", 2)
            self.tama.ganhar_xp(2)
            self.falar("Rolei! 🥚", 1.5)
            return
        if self.tama.ativo and self.estado.status["energia"] < 15:
            self.falar("Tô cansadinho... 😴")
            return
        self.mudar("comemorando", 2.6)
        self._ajustar("felicidade", 10)
        self._ajustar("energia", -5)
        self._ajustar("fome", -3)
        self.tama.ganhar_xp(config.XP_BRINCAR)
        self.falar("Iupi!")

    def _dormir_ou_acordar(self):
        if self.acao == "dormindo":
            self.acordar("Bom dia! ☀️")
        else:
            self.dormir()

    def dormir(self, texto="Boa noite... 💤"):
        # Sem prazo: o Tamagotchi acorda ele quando a energia enche (ou um clique)
        self.mudar("dormindo")
        self.falar(texto, 2.5)

    def acordar(self, texto="Que soneca boa!"):
        self.tama.acordado_em = time.time()
        self.mudar("parado", 2)
        self.falar(texto, 2)

    def dar_remedio(self):
        if not self.estado.dados["doente"]:
            self.falar("Não tô doente! 💪", 2)
            return
        self.estado.dados["doente"] = False
        self.estado.dados["horas_com_fome"] = 0.0
        self.mudar("comendo", 1.5)
        self.tama.ganhar_xp(config.XP_REMEDIO)
        self.falar("Eca, que gosto ruim...\nmas já tô melhor! 💊", 3)
        self.salvar()

    def espirrar(self):
        self.mudar("espirrando", 1.2)
        self.falar("Atchim! 🤧", 1.2)
        self.root.after(300, lambda: self.efeitos.gotas(
            self.larg_janela / 2 + 4 * self.escala * self.direcao,
            self.alt_janela - self.sprites.altura_corpo / 2, self.direcao))

    def bolha_em(self, x_tela, y_tela):
        """Bolha de sabão onde o mouse está esfregando."""
        self.efeitos.bolha(x_tela - self.root.winfo_rootx(), y_tela - self.root.winfo_rooty())

    def mostrar_status(self):
        self.painel.abrir()

    # ------------------------------------------------------------------ evolução

    def verificar_evolucao(self):
        """Evolui quando o XP passa do mínimo da próxima fase (nunca regride)."""
        nova = necessidades.fase_por_xp(self.estado.dados["xp"])
        ordem = necessidades.ORDEM_FASE
        if self.demo or ordem[nova] <= ordem[self.fase] or self.acao not in ("parado", "andando"):
            return
        if self.fase == "ovo":
            # Primeiro a casca racha, depois ele nasce (_fim_da_acao chama _evoluir)
            self._fase_pendente = nova
            self.mudar("chocando", 3)
            self.falar("Crec... crec...", 2.5)
        else:
            self._evoluir(nova)

    def _evoluir(self, nova):
        antiga = self.fase
        self.fase = nova
        self.estado.dados["fase"] = nova
        self.sprites = self._biblioteca(nova)
        self._ajustar_janela()
        self._img_atual = None
        self.mudar("comemorando", 3)
        if antiga == "ovo":
            self.falar("Nasci! 🐣\nOi, eu sou o Clawd!", 4)
        else:
            self.falar(f"Evoluí! Agora sou\n{necessidades.NOMES_FASE[nova]}! ✨", 4)
        self.salvar()

    def _ajustar_janela(self):
        # PNGs de fases diferentes podem ter tamanhos diferentes
        e = self.escala
        larg = self.sprites.largura_max + 2 * config.MARGEM_LATERAL * e
        alt = self.sprites.altura_max + config.MARGEM_TOPO * e
        if (larg, alt) != (self.larg_janela, self.alt_janela):
            self.larg_janela, self.alt_janela = larg, alt
            self.canvas.config(width=larg, height=alt)
            self.canvas.coords(self.item_sprite, larg / 2, alt)
            self._pos_janela = None

    def mostrar_clima(self):
        self.falar("Ainda não sei olhar o céu...\n(o clima chega na fase 4) ☁️", 4)

    # ------------------------------------------------------------------ mouse

    def _apertou(self, e):
        self.apertado_em = (e.x_root, e.y_root)
        self.arrastando = False
        self.pegada = (e.x_root - self.corpo.x, e.y_root - (self.corpo.y - self.salto))
        self.amostras = [(time.perf_counter(), e.x_root, e.y_root)]
        self.detector.reiniciar()

    def _moveu(self, e):
        if self.apertado_em is None:
            return
        if not self.arrastando:
            if not interacao.eh_arrasto(self.apertado_em, (e.x_root, e.y_root), config.LIMIAR_CLIQUE):
                return
            self._comecar_arrasto()
        agora = time.perf_counter()
        self.corpo.x = e.x_root - self.pegada[0]
        self.corpo.y = e.y_root - self.pegada[1]
        self.amostras.append((agora, e.x_root, e.y_root))
        self.amostras = [a for a in self.amostras if agora - a[0] <= 0.25]
        if self.detector.adicionar(agora, e.x_root, e.y_root) and not self.tonto_pendente:
            self.tonto_pendente = True
            self.efeitos.estrelas_girando(True)
            self.falar("Para, para! 😵", 1.5)

    def _comecar_arrasto(self):
        self.arrastando = True
        if self.acao == "dormindo":
            self.falar("Ei! Eu tava dormindo!", 1.5)
        self.corpo.y -= self.salto
        self.salto = self.salto_v = 0.0
        self.mudar("pendurado")

    def _soltou(self, e):
        if self.apertado_em is None:
            return
        self.apertado_em = None
        if not self.arrastando:
            self._clique()
            return
        self.arrastando = False
        vx, vy = interacao.estimar_velocidade(self.amostras, time.perf_counter())
        if (vx * vx + vy * vy) ** 0.5 >= config.LIMIAR_ARREMESSO * self.k:
            vx, vy = fisica.limitar_velocidade(vx, vy, self.params.vel_max)
            self.arremessado = True
            if not self.tonto_pendente:
                self.falar("Uhuuul! 🚀", 1.2)
        else:
            vx = vy = 0.0
            self.arremessado = False
        self.corpo.vx, self.corpo.vy = vx, vy
        self.corpo.no_chao = False
        # Solto em cima de outro monitor: passa a morar nele
        onde = tela.monitor_no_ponto(self.monitores, e.x_root, e.y_root)
        if onde.nome != self.monitor.nome:
            self.monitor = onde
            self.area = onde.area
            lim = self._limites()
            self.corpo.x = min(max(self.corpo.x, lim.esquerda + lim.meia_largura), lim.direita - lim.meia_largura)
            self.corpo.y = min(max(self.corpo.y, lim.topo + lim.altura), lim.chao)
        if vx:
            self.direcao = 1 if vx > 0 else -1
        self.mudar("caindo")

    def _clique(self):
        """Carinho: coraçãozinho e um pouco de felicidade."""
        if self.acao == "dormindo":
            self.acordar("Hm? Acordei!")
            return
        self.efeitos.coracao(self.larg_janela / 2, self._cabeca_no_canvas() - 2 * self.escala)
        self.tama.carinho()
        if random.random() < 0.3:
            self.falar(random.choice(FALAS_CARINHO), 1.5)

    def _abrir_menu(self, e):
        if self.acao == "andando":
            self.mudar("parado", 5)    # não sai andando com o menu aberto
        try:
            self.menu.tk_popup(e.x_root, e.y_root)
            self.menu.grab_release()
        except tk.TclError:
            pass    # "Sair" fecha a janela antes do menu terminar de voltar

    # ------------------------------------------------------------------ loop

    def _tick(self):
        try:
            agora = time.perf_counter()
            dt = min(agora - self._ultimo_tick, 0.05)   # evita saltos se o PC engasgar
            self._ultimo_tick = agora
            self._atualizar(agora, dt)
            self._desenhar(agora)
        except Exception:
            log.exception("Erro no tick")
        finally:
            self.root.after(config.TICK_MS, self._tick)

    def _atualizar(self, agora, dt):
        a = self.acao
        if a == "caindo":
            self._passo_fisica(dt)
        elif a == "andando":
            self._andar(dt)
        elif a == "comemorando" and self.salto <= 0:
            self.salto_v = config.VEL_PULO * self.k     # pula de novo assim que encosta no chão
        elif a == "dormindo" and agora >= self._prox_particula:
            self._prox_particula = agora + 1.3
            self.efeitos.zzz(self.larg_janela / 2 + 5 * self.escala * self.direcao,
                             self._cabeca_no_canvas() + 2 * self.escala, self.direcao)
        elif a == "comendo" and agora >= self._prox_particula and self.fase != "ovo":
            self._prox_particula = agora + 0.35
            boca_y = self.alt_janela - self.sprites.altura_corpo * 0.45
            self.efeitos.migalhas(self.larg_janela / 2, boca_y)

        # Pulinho (continua até encostar no chão mesmo depois da comemoração acabar)
        if self.salto > 0 or self.salto_v > 0:
            self.salto_v -= self.params.gravidade * dt
            self.salto = max(0.0, self.salto + self.salto_v * dt)
            if self.salto == 0:
                self.salto_v = 0.0

        if self.acao_ate is not None and agora >= self.acao_ate:
            self._fim_da_acao()

        self.tama.tick()
        self.efeitos.atualizar(dt, self.larg_janela / 2, self._cabeca_no_canvas() - 2 * self.escala,
                               self.alt_janela - self.sprites.altura_corpo / 2)

    def _andar(self, dt):
        lim = self._limites()
        velocidade = config.VELOCIDADE_ANDAR * self.k
        if self.tama.ativo and (self.estado.dados["doente"] or self.estado.status["energia"] < 30):
            velocidade *= 0.5      # cansado ou gripado anda devagar
        self.corpo.x += self.direcao * velocidade * dt
        # Vira quando chega na borda da tela
        if self.corpo.x - lim.meia_largura <= lim.esquerda:
            self.corpo.x = lim.esquerda + lim.meia_largura
            self.direcao = 1
        elif self.corpo.x + lim.meia_largura >= lim.direita:
            self.corpo.x = lim.direita - lim.meia_largura
            self.direcao = -1

    def _passo_fisica(self, dt):
        for nome, vel in fisica.passo(self.corpo, self._limites(), self.params, dt):
            agora = time.perf_counter()
            if nome in ("parede", "teto") and vel > config.VEL_AI * self.k and agora - self._ultimo_ai > 1:
                self._ultimo_ai = agora
                self.falar("Ai!", 0.8)
            if nome == "parede":
                self.direcao = 1 if self.corpo.vx > 0 else -1
            if nome == "pousou":
                self._pousou()
                break

    def _pousou(self):
        if not self.demo:
            # Lugar favorito: onde foi solto por último
            self.estado.dados["lugar_favorito"] = {"x": round(self.corpo.x), "y": round(self.corpo.y)}
            self.estado.dados["monitor"] = self.monitor.nome
            self.salvar()
        if self.tonto_pendente:
            self.mudar("tonto", config.TONTO_SEGUNDOS)
            self._ajustar("felicidade", -config.PERDA_TONTURA)
            self.falar("Tô tontinho... 😵", 2.5)
        else:
            if self.arremessado:
                self.falar(random.choice(FALAS_POUSO), 1.5)
            self.mudar("parado", random.uniform(1.5, 3))
        self.arremessado = False

    # ------------------------------------------------------------------ desenho

    def _cabeca_no_canvas(self):
        """Altura do topo da cabeça dentro do canvas."""
        return self.alt_janela - self.sprites.altura_corpo

    def _desenhar(self, agora):
        anim = self.acao if self.acao in self.sprites.animacoes else "parado"
        img = self.sprites.quadro(anim, (agora - self.anim_inicio) * 1000, self.direcao < 0)
        if img is not self._img_atual:
            self.canvas.itemconfig(self.item_sprite, image=img)
            self._img_atual = img
        pes_y = self.corpo.y - self.salto
        pos = (round(self.corpo.x - self.larg_janela / 2), round(pes_y - self.alt_janela))
        if pos != self._pos_janela:
            self.root.geometry(f"+{pos[0]}+{pos[1]}")
            self._pos_janela = pos
        self.balao.atualizar(self.corpo.x, pes_y - self.sprites.altura_corpo - self.escala, self.area)

    # ------------------------------------------------------------------ demo

    DEMO = [
        ("acenando", "Oi! Essa é a demo 👋"),
        ("parado", "parado"),
        ("andando", "andando"),
        ("comendo", "comendo 🍤"),
        ("comemorando", "comemorando!"),
        ("dormindo", "dormindo 💤"),
        ("pendurado", "pendurado"),
        ("caindo", "caindo!"),
        ("tonto", "tonto 😵"),
        ("escondido", "escondido"),
        ("espirrando", "espirrando 🤧"),
        ("chocando", "chocando 🥚"),
    ]

    def _demo(self, i):
        """Passa por todas as animações, 3,5 s cada. Uso: python main.py --demo [--fase anciao]"""
        if i >= len(self.DEMO):
            self.efeitos.estrelas_girando(False)
            self.corpo.y = self.area.base
            self.mudar("parado", 2)
            self.falar("Fim da demo!", 2)
            return
        acao, texto = self.DEMO[i]
        if acao not in self.sprites.animacoes:
            self._demo(i + 1)       # ex.: só o ovo choca, só o Clawd espirra
            return
        self.efeitos.estrelas_girando(acao == "tonto")
        if acao == "pendurado":
            self.corpo.y = self.area.base - 120 * self.k
        elif acao == "caindo":
            self.corpo.vx = self.corpo.vy = 0.0
            self.corpo.no_chao = False
        else:
            self.corpo.y = self.area.base
        self.mudar(acao, 3.5 if acao not in ("caindo", "pendurado") else None)
        if acao == "tonto":
            self.tonto_pendente = True
        self.falar(texto, 3)
        self.root.after(3500, self._demo, i + 1)
