"""Música: quando sai som do PC por uns segundos, ele põe o fone e dança.

O volume vem do medidor de pico do Windows (Core Audio), chamado direto pelo
ctypes, sem instalar nada. Fica numa thread; DetectorDeMusica é puro e testável.
"""

import ctypes
import logging
import random
import threading
import time
import uuid

log = logging.getLogger(__name__)

LIMIAR = 0.01                 # pico acima disso = tem som saindo
SEGUNDOS_PRA_COMECAR = 4      # som seguido por esse tempo = música (bipe e notificação não contam)
BURACO_TOLERADO = 1.5         # pausinha entre faixas ou batidas não interrompe
SEGUNDOS_PRA_PARAR = 8        # silêncio por esse tempo = acabou


class DetectorDeMusica:
    def __init__(self):
        self.tocando = False
        self._comecou = None       # início do som seguido atual
        self._ultimo_som = None

    def medir(self, pico, agora):
        """Recebe o volume (0 a 1) e devolve se tem música tocando."""
        if pico > LIMIAR:
            if self._ultimo_som is None or agora - self._ultimo_som > BURACO_TOLERADO:
                self._comecou = agora
            self._ultimo_som = agora
            if agora - self._comecou >= SEGUNDOS_PRA_COMECAR:
                self.tocando = True
        elif self._ultimo_som is None or agora - self._ultimo_som >= SEGUNDOS_PRA_PARAR:
            self.tocando = False
        return self.tocando


# ---------------------------------------------------------------------- Core Audio pelo ctypes

class _GUID(ctypes.Structure):
    _fields_ = [("bytes", ctypes.c_ubyte * 16)]

    @classmethod
    def de(cls, texto):
        return cls.from_buffer_copy(uuid.UUID(texto).bytes_le)


CLSID_ENUMERADOR = "BCDE0395-E52F-467C-8E3D-C4579291692E"
IID_ENUMERADOR = "A95664D2-9614-4F35-A746-DE8DB63617E6"
IID_MEDIDOR = "C02216F6-8C67-4B5B-9D00-D008E73E0064"
CLSCTX_ALL = 0x17


def _metodo(objeto, indice, *argumentos):
    """Função número `indice` da tabela de métodos de um objeto COM."""
    tabela = ctypes.cast(objeto, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    prototipo = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argumentos)
    return lambda *valores: prototipo(tabela[indice])(objeto, *valores)


class MedidorDoWindows:
    """Pico de volume da saída de som padrão (o mesmo verdinho do mixer do Windows)."""

    def __init__(self):
        self._ole32 = ctypes.windll.ole32
        self._enumerador = None
        self._medidor = None
        self._prox_dispositivo = 0.0

    def _soltar(self, objeto):
        if objeto:
            _metodo(objeto, 2)()                       # Release

    def _pegar_medidor(self):
        self._soltar(self._medidor)
        self._medidor = None
        if self._enumerador is None:
            enumerador = ctypes.c_void_p()
            if self._ole32.CoCreateInstance(ctypes.byref(_GUID.de(CLSID_ENUMERADOR)), None, CLSCTX_ALL,
                                            ctypes.byref(_GUID.de(IID_ENUMERADOR)), ctypes.byref(enumerador)):
                return
            self._enumerador = enumerador
        dispositivo = ctypes.c_void_p()
        # GetDefaultAudioEndpoint(eRender, eMultimedia)
        if _metodo(self._enumerador, 4, ctypes.c_int, ctypes.c_int, ctypes.c_void_p)(
                0, 1, ctypes.byref(dispositivo)) or not dispositivo:
            return                                   # sem saída de som
        medidor = ctypes.c_void_p()
        _metodo(dispositivo, 3, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p)(
            ctypes.byref(_GUID.de(IID_MEDIDOR)), CLSCTX_ALL, None, ctypes.byref(medidor))   # Activate
        self._soltar(dispositivo)
        self._medidor = medidor if medidor else None

    def pico(self):
        agora = time.time()
        if self._medidor is None or agora >= self._prox_dispositivo:
            self._prox_dispositivo = agora + 30        # fone plugado muda a saída padrão
            self._pegar_medidor()
        if self._medidor is None:
            return 0.0
        valor = ctypes.c_float()
        if _metodo(self._medidor, 3, ctypes.c_void_p)(ctypes.byref(valor)):         # GetPeakValue
            self._medidor = None
            return 0.0
        return valor.value


# ---------------------------------------------------------------------- ligado ao pet

class Musica:
    def __init__(self, mascote, criar_medidor=MedidorDoWindows):
        self.m = mascote
        self.d = mascote.estado.dados["rotina"]
        self.criar_medidor = criar_medidor
        self.detector = DetectorDeMusica()
        self.ativa = False           # o pet está de fone agora
        self._thread = None
        self._parar = threading.Event()
        self._prox = 0.0
        self._prox_nota = 0.0

    @property
    def ligado(self):
        return self.d["musica"]

    def alternar(self):
        self.d["musica"] = not self.d["musica"]

    def roupas(self):
        return {"fone"} if self.ativa else set()

    def _ouvir(self):
        """Thread: lê o volume 4 vezes por segundo enquanto a opção estiver ligada."""
        try:
            ctypes.windll.ole32.CoInitializeEx(None, 0)
            medidor = self.criar_medidor()
        except (AttributeError, OSError):
            log.info("Sem medidor de som: o pet não vai dançar")
            return
        while not self._parar.is_set():
            try:
                self.detector.medir(medidor.pico(), time.time())
            except OSError:
                log.exception("Erro lendo o volume")
                return
            self._parar.wait(0.25)

    def parar(self):
        self._parar.set()

    def tick(self):
        agora = time.time()
        if self.ligado and (self._thread is None or not self._thread.is_alive()) and not self._parar.is_set():
            self._thread = threading.Thread(target=self._ouvir, daemon=True)
            self._thread.start()
        if agora >= self._prox:
            self._prox = agora + 0.5
            tocando = self.ligado and self.detector.tocando
            if tocando != self.ativa:
                self.ativa = tocando
                self.m.atualizar_roupas()
                if tocando and not self.m.balao.visivel and random.random() < 0.4:
                    self.m.falar("🎧 Que som bom!", 2)
                elif not tocando and self.m.acao == "dancando":
                    self.m.mudar("parado", 1.5)
        m = self.m
        if self.ativa and agora >= self._prox_nota and m.acao in ("parado", "andando", "dancando", "digitando"):
            self._prox_nota = agora + random.uniform(0.9, 1.6)
            m.efeitos.nota(m.larg_janela / 2 + 6 * m.escala * m.direcao,
                           m.alt_janela - m.sprites.altura_corpo, m.direcao)

    def quer_dancar(self):
        """Na hora de escolher o que fazer: com música, dança bastante."""
        return self.ativa and self.m.fase != "ovo" and random.random() < 0.45
