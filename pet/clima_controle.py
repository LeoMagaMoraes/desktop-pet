"""Liga o clima ao pet: busca numa thread a cada 30 min, troca as roupas (guarda-chuva
na chuva, óculos no sol...), avisa da previsão de manhã e se esconde na trovoada.
Sem internet, continua com o último clima que conseguiu."""

import logging
import random
import threading
import time
from datetime import datetime, timedelta

from . import clima, config, especies, tela
from .clima import Clima

log = logging.getLogger(__name__)

# Sigla do estado -> nome, pra aceitar "Florianópolis, SC" na troca de cidade
UFS = {"AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará",
       "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
       "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais", "PA": "Pará",
       "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro",
       "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima",
       "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins"}


def ler_cidade(texto):
    """'Florianópolis, SC' -> ('Florianópolis', 'Santa Catarina'); 'Recife' -> ('Recife', None)."""
    partes = [p.strip() for p in (texto or "").replace(" - ", ",").replace("-", ",").split(",") if p.strip()]
    if not partes:
        return None, None
    estado = None
    if len(partes) > 1:
        estado = UFS.get(partes[1].upper(), partes[1])
    return partes[0], estado


class ControleClima:
    def __init__(self, mascote):
        self.m = mascote
        self.d = mascote.estado.dados["clima"]
        self.d.pop("chuva_na_tela", None)       # opção das gotas na tela, que saiu
        self.atual = None
        if self.d.get("atual"):
            try:
                self.atual = Clima.do_save(self.d["atual"])
            except (KeyError, TypeError, ValueError):
                log.warning("Clima salvo ilegível, ignorando")
        self.baixar = clima._baixar_json     # troca nos testes
        self.erro = None
        self._resultado = None                # o que a thread trouxe (o Tk só mexe na thread principal)
        self._thread = None
        self._prox_busca = 0.0
        self._prox_checagem = 0.0
        self._prox_trovao = 0.0
        self._prox_neblina = time.time() + 300

    # ------------------------------------------------------------------ leitura

    def agora_na_cidade(self):
        return clima.agora_na_cidade(self.d.get("utc_offset", -10800))

    def vigente(self):
        """O clima que vale agora. Se for velho (sem internet), dia/noite vem do relógio."""
        c = self.atual
        if c is None:
            return None
        agora = self.agora_na_cidade()
        if agora - c.hora_local > timedelta(hours=2):
            c = Clima(c.temperatura, c.sensacao, c.codigo, 6 <= agora.hour < 18, c.vento, c.hora_local,
                      c.chuva_por_hora)
        return c

    def roupas(self):
        c = self.vigente()
        return especies.ajustar_roupas(self.m.especie, clima.roupas(c), c)    # cada bicho do seu jeito

    def efeitos(self):
        c = self.vigente()
        return especies.ajustar_efeitos(self.m.especie, clima.efeitos_nos_status(c), c)

    def rotulo(self):
        """'23° ☀' pro menu, ou '' se ainda não sabe."""
        c = self.vigente()
        return f"{round(c.temperatura)}° {c.emoji}" if c else ""

    # ------------------------------------------------------------------ busca (thread)

    def atualizar_agora(self):
        self._prox_busca = 0.0
        self._prox_checagem = 0.0

    def trocar_cidade(self, texto):
        nome, estado = ler_cidade(texto)
        if not nome:
            return False
        self.d.update(cidade=nome, estado=estado, lat=None, lon=None, nome_exibido=None)
        self.atualizar_agora()
        self.m.falar(f"Procurando {nome}... 🔎", 2)
        return True

    def _buscar(self):
        """Roda na thread: acha a cidade (só da primeira vez) e baixa a previsão."""
        try:
            d = dict(self.d)
            if d.get("lat") is None:
                achada = clima.procurar_cidade(d["cidade"], d.get("estado"), d.get("pais") or "BR",
                                               baixar=self.baixar)
                if achada is None:
                    self._resultado = ("cidade", f"Não achei a cidade {d['cidade']} 🤔")
                    return
                nome, estado, lat, lon = achada
                d.update(nome_exibido=nome, estado=estado, lat=lat, lon=lon)
            bruto = self.baixar(clima.URL_PREVISAO, {
                "latitude": d["lat"], "longitude": d["lon"], "timezone": "auto", "forecast_days": 1,
                "current": "temperature_2m,apparent_temperature,weather_code,is_day,wind_speed_10m",
                "hourly": "precipitation_probability"})
            self._resultado = ("ok", d, clima.ler_previsao(bruto), bruto.get("utc_offset_seconds", -10800))
        except Exception as erro:          # sem internet, site fora do ar, JSON estranho...
            self._resultado = ("erro", str(erro))

    # ------------------------------------------------------------------ loop

    def tick(self):
        agora = time.time()
        if agora < self._prox_checagem:
            return
        self._prox_checagem = agora + 1

        if self._resultado is not None:
            self._aplicar(self._resultado)
            self._resultado = None
        if agora >= self._prox_busca and (self._thread is None or not self._thread.is_alive()):
            self._prox_busca = agora + config.MINUTOS_CLIMA * 60
            self._thread = threading.Thread(target=self._buscar, daemon=True)
            self._thread.start()

        self._vestir()
        self._previsao_da_manha()
        self._comportamento(agora)

    def _aplicar(self, resultado):
        if resultado[0] == "ok":
            _, cidade, novo, offset = resultado
            antes = self.atual
            self.d.update(cidade=cidade["cidade"], estado=cidade.get("estado"), lat=cidade["lat"],
                          lon=cidade["lon"], nome_exibido=cidade.get("nome_exibido"), utc_offset=offset,
                          atual=novo.para_save(),
                          atualizado=datetime.now().astimezone().isoformat(timespec="minutes"))
            self.atual = novo
            self.erro = None
            if antes is None or antes.categoria != novo.categoria:
                self._comentar_mudanca(novo)
        elif resultado[0] == "cidade":
            self.erro = resultado[1]
            self.m.falar(resultado[1], 3)
        else:
            # Sem internet: fica com o último clima e tenta de novo daqui a pouco
            self.erro = resultado[1]
            self._prox_busca = min(self._prox_busca, time.time() + 300)
            log.info("Clima indisponível: %s", resultado[1])

    def _comentar_mudanca(self, c):
        frases = {"limpo": "Que solzão! 😎" if c.eh_dia else "Noite limpinha 🌙",
                  "chuva": "Começou a chover! ☔", "garoa": "Tá garoando... ☔",
                  "neve": "NEVE?! ❄️", "neblina": "Que neblina... 🌫", "tempestade": None, "nublado": None}
        texto = frases.get(c.categoria)
        if texto and not self.m.balao.visivel:
            self.m.falar(texto, 2.5)

    def _vestir(self):
        m = self.m
        m.vestir(self.roupas())
        c = self.vigente()
        calor = especies.especie(m.especie).calor          # o pinguim sente calor antes
        m.efeitos.ventilador_ligado(bool(c and c.temperatura > calor and m.fase != "ovo"))

    def _previsao_da_manha(self):
        """Uma vez por dia, de manhã: se vai chover mais tarde, ele avisa."""
        c = self.atual
        agora = self.agora_na_cidade()
        hoje = agora.date().isoformat()
        if (c is None or self.d.get("previsao_avisada") == hoje or not 6 <= agora.hour < 12
                or c.hora_local.date() != agora.date() or self.m.balao.visivel
                or tela.segundos_ocioso() > 120):
            return
        self.d["previsao_avisada"] = hoje
        chuva = clima.proxima_chuva(c, agora)
        if chuva:
            hora, chance = chuva
            self.m.falar(f"☔ Previsão: deve chover lá pelas {hora.hour}h ({chance}%).\n"
                         "Não esquece o guarda-chuva!", 6)

    def _comportamento(self, agora):
        m = self.m
        c = self.vigente()
        trovoada = c is not None and c.categoria == "tempestade" and "tremendo" in m.sprites.animacoes
        if trovoada and m.acao in ("parado", "andando"):
            m.mudar("tremendo")
        elif not trovoada and m.acao == "tremendo":
            m.mudar("parado", 2)
        if trovoada and m.acao == "tremendo" and agora >= self._prox_trovao and not m.balao.visivel:
            self._prox_trovao = agora + random.uniform(90, 180)
            m.falar("Tá trovejando! 😱", 2.5)
        if c and c.categoria == "neblina" and agora >= self._prox_neblina and m.acao == "andando":
            self._prox_neblina = agora + 1200
            m.falar("Não tô enxergando nada... 🌫", 2)

    # ------------------------------------------------------------------ balões

    def texto_clique(self):
        """O que ele fala quando você clica nele."""
        c = self.vigente()
        if c is None:
            return None
        return f"{c.emoji} {round(c.temperatura)}°C · {c.descricao}"

    def mostrar(self):
        c = self.vigente()
        cidade = self.d.get("nome_exibido") or self.d.get("cidade") or "?"
        if c is None:
            self.m.falar("Ainda não sei o clima... 🤔\n" + ("(sem internet?)" if self.erro else "procurando!"), 3)
            return
        texto = clima.resumo(c, cidade, self.agora_na_cidade())
        if self.erro:
            texto += "\n(sem internet: esse é o último que eu vi)"
        self.m.falar(texto, 6)
