"""Acesso à API do Windows: DPI, monitores, área de trabalho, estilo da janela e instância única."""

import ctypes
import re
import sys
from dataclasses import dataclass

WINDOWS = sys.platform == "win32"

if WINDOWS:
    from ctypes import wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _user32.GetParent.argtypes = [wintypes.HWND]
    _user32.GetParent.restype = wintypes.HWND
    _user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    _user32.GetWindowLongW.restype = ctypes.c_long
    _user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    _user32.SetWindowLongW.restype = ctypes.c_long
    _kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    _kernel32.CreateMutexW.restype = wintypes.HANDLE

    class _MONITORINFOEXW(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT),
                    ("dwFlags", wintypes.DWORD), ("szDevice", wintypes.WCHAR * 32)]

    _MonitorEnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                                          ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    _user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.c_void_p, _MonitorEnumProc, wintypes.LPARAM]
    _user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(_MONITORINFOEXW)]
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    _kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                     ctypes.POINTER(wintypes.DWORD)]
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    # Janelas abertas (pro pet andar em cima delas)
    _WndEnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    _user32.EnumWindows.argtypes = [_WndEnumProc, wintypes.LPARAM]
    _user32.IsWindowVisible.argtypes = [wintypes.HWND]
    _user32.IsIconic.argtypes = [wintypes.HWND]
    _user32.IsZoomed.argtypes = [wintypes.HWND]
    _user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    _user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    _user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    _user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    try:
        _dwmapi = ctypes.WinDLL("dwmapi")
        _dwmapi.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    except OSError:
        _dwmapi = None

SPI_GETWORKAREA = 0x30
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x80
WS_EX_APPWINDOW = 0x40000
ERROR_ALREADY_EXISTS = 183
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
MONITORINFOF_PRIMARY = 1


@dataclass(frozen=True)
class Area:
    """Retângulo da tela sem a barra de tarefas. `base` é o topo da barra."""
    esquerda: int
    topo: int
    direita: int
    base: int

    def contem(self, x, y):
        return self.esquerda <= x < self.direita and self.topo <= y < self.base

    def distancia(self, x, y):
        """Distância de um ponto até o retângulo (0 se estiver dentro)."""
        dx = max(self.esquerda - x, 0, x - self.direita)
        dy = max(self.topo - y, 0, y - self.base)
        return (dx * dx + dy * dy) ** 0.5


@dataclass(frozen=True)
class Monitor:
    nome: str          # nome do Windows, ex.: \\.\DISPLAY2 (é o que vai pro save)
    numero: int        # o número de "Configurações > Tela"
    tela: Area         # monitor inteiro
    area: Area         # sem a barra de tarefas; o chão do Clawd é area.base
    principal: bool

    @property
    def rotulo(self):
        largura = self.tela.direita - self.tela.esquerda
        altura = self.tela.base - self.tela.topo
        extra = " (principal)" if self.principal else ""
        return f"Monitor {self.numero} · {largura}×{altura}{extra}"


def ativar_dpi():
    """Pede pixels reais ao Windows (sem isso a arte fica borrada em telas com zoom)."""
    if not WINDOWS:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def area_de_trabalho(root=None):
    """Área útil do monitor principal; o chão do Clawd é a borda de baixo dela."""
    if WINDOWS:
        r = wintypes.RECT()
        if _user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(r), 0):
            return Area(r.left, r.top, r.right, r.bottom)
    if root is not None:
        return Area(0, 0, root.winfo_screenwidth(), root.winfo_screenheight())
    return Area(0, 0, 1920, 1080)


def monitores(root=None):
    """Monitores ligados, com o principal primeiro e o resto da esquerda pra direita."""
    lista = []
    if WINDOWS:
        def cada(hmonitor, _hdc, _rect, _dados):
            info = _MONITORINFOEXW()
            info.cbSize = ctypes.sizeof(_MONITORINFOEXW)
            if _user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
                m, w = info.rcMonitor, info.rcWork
                achado = re.search(r"(\d+)$", info.szDevice)
                lista.append(Monitor(
                    nome=info.szDevice,
                    numero=int(achado.group(1)) if achado else len(lista) + 1,
                    tela=Area(m.left, m.top, m.right, m.bottom),
                    area=Area(w.left, w.top, w.right, w.bottom),
                    principal=bool(info.dwFlags & MONITORINFOF_PRIMARY)))
            return True
        _user32.EnumDisplayMonitors(None, None, _MonitorEnumProc(cada), 0)
    if not lista:
        area = area_de_trabalho(root)
        lista.append(Monitor("principal", 1, area, area, True))
    return sorted(lista, key=lambda m: (not m.principal, m.tela.esquerda, m.tela.topo))


def monitor_por_nome(lista, nome):
    """O monitor salvo, ou o principal se ele não estiver mais ligado."""
    for m in lista:
        if m.nome == nome:
            return m
    return lista[0]


def monitor_no_ponto(lista, x, y):
    """Monitor que contém o ponto; se cair entre monitores, o mais próximo."""
    for m in lista:
        if m.tela.contem(x, y):
            return m
    return min(lista, key=lambda m: m.tela.distancia(x, y))


def estilo_ferramenta(janela):
    """Tira a janela do Alt+Tab e da barra de tarefas."""
    if not WINDOWS:
        return
    hwnd = _user32.GetParent(janela.winfo_id()) or janela.winfo_id()
    estilo = _user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    _user32.SetWindowLongW(hwnd, GWL_EXSTYLE, (estilo | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW)


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def segundos_ocioso():
    """Há quanto tempo ninguém mexe no mouse ou no teclado."""
    if not WINDOWS:
        return 0.0
    info = _LASTINPUTINFO(ctypes.sizeof(_LASTINPUTINFO), 0)
    if not _user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    agora = _kernel32.GetTickCount() & 0xFFFFFFFF
    return ((agora - info.dwTime) & 0xFFFFFFFF) / 1000


def programa_em_primeiro_plano():
    """Nome do .exe da janela ativa, em minúsculas (ex.: 'windowsterminal.exe'), ou ''."""
    if not WINDOWS:
        return ""
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return ""
    pid = wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    processo = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not processo:
        return ""
    try:
        tamanho = wintypes.DWORD(1024)
        caminho = ctypes.create_unicode_buffer(tamanho.value)
        if not _kernel32.QueryFullProcessImageNameW(processo, 0, caminho, ctypes.byref(tamanho)):
            return ""
        return caminho.value.rsplit("\\", 1)[-1].lower()
    finally:
        _kernel32.CloseHandle(processo)


def cantos_arredondados(janela):
    """Pede pro Windows 11 arredondar os cantos da janela (no 10 não faz nada)."""
    if not WINDOWS:
        return
    try:
        hwnd = _user32.GetParent(janela.winfo_id()) or janela.winfo_id()
        preferencia = ctypes.c_int(2)          # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(preferencia),
                                                   ctypes.sizeof(preferencia))
    except (AttributeError, OSError):
        pass


@dataclass(frozen=True)
class JanelaAberta:
    """Uma janela de outro programa: o retângulo visível (sem as bordas invisíveis do Windows)."""
    hwnd: int
    esquerda: int
    topo: int
    direita: int
    base: int
    titulo: str = ""


# Classes de janela que não são "janelas de verdade" (área de trabalho, barra de tarefas...)
CLASSES_IGNORADAS = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
                     "NotifyIconOverflowWindow", "Windows.UI.Core.CoreWindow", "TopLevelWindowForOverflowXamlIsland",
                     "XamlExplorerHostIslandWindow", "SysShadow", "tooltips_class32"}
DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14


def _retangulo_visivel(hwnd):
    r = wintypes.RECT()
    if _dwmapi is not None and _dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(r), ctypes.sizeof(r)) == 0:
        return r
    _user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r


def _escondida_pelo_windows(hwnd):
    """Janelas "camufladas" (apps de outra área de trabalho virtual, apps UWP fechados)."""
    if _dwmapi is None:
        return False
    camuflada = ctypes.c_int(0)
    _dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(camuflada), ctypes.sizeof(camuflada))
    return camuflada.value != 0


def janelas_visiveis(tamanho_minimo=120):
    """Janelas abertas e visíveis dos outros programas, da mais da frente pra mais do fundo."""
    if not WINDOWS:
        return []
    import os
    meu_pid = os.getpid()
    achadas = []

    def cada(hwnd, _):
        if not _user32.IsWindowVisible(hwnd) or _user32.IsIconic(hwnd):
            return True
        if _user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
            return True
        pid = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == meu_pid:
            return True                     # o próprio pet, o balão, o menu...
        classe = ctypes.create_unicode_buffer(128)
        _user32.GetClassNameW(hwnd, classe, 128)
        if classe.value in CLASSES_IGNORADAS or _escondida_pelo_windows(hwnd):
            return True
        tamanho = _user32.GetWindowTextLengthW(hwnd)
        if tamanho == 0:
            return True                     # janelas sem título costumam ser invisíveis/auxiliares
        r = _retangulo_visivel(hwnd)
        if r.right - r.left < tamanho_minimo or r.bottom - r.top < tamanho_minimo // 2:
            return True
        titulo = ctypes.create_unicode_buffer(tamanho + 1)
        _user32.GetWindowTextW(hwnd, titulo, tamanho + 1)
        achadas.append(JanelaAberta(int(hwnd), r.left, r.top, r.right, r.bottom, titulo.value))
        return True

    _user32.EnumWindows(_WndEnumProc(cada), 0)
    return achadas


def tela_cheia_em(area):
    """True se a janela ativa (de outro programa) cobre o monitor inteiro: jogo, filme, apresentação.

    Usa o retângulo visível: janela só maximizada deixa a barra de tarefas (ou uma
    beiradinha dela, se ela se esconde sozinha) de fora, então não conta.
    """
    if not WINDOWS:
        return False
    import os
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return False
    pid = wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == os.getpid():
        return False
    classe = ctypes.create_unicode_buffer(128)
    _user32.GetClassNameW(hwnd, classe, 128)
    if classe.value in CLASSES_IGNORADAS:
        return False                        # área de trabalho e barra de tarefas também "cobrem" a tela
    r = _retangulo_visivel(hwnd)
    return r.left <= area.esquerda and r.top <= area.topo and r.right >= area.direita and r.bottom >= area.base


def botao_do_mouse_apertado():
    """True se o botão esquerdo, direito ou do meio está apertado agora (em qualquer janela)."""
    if not WINDOWS:
        return False
    return any(_user32.GetAsyncKeyState(tecla) & 0x8000 for tecla in (0x01, 0x02, 0x04))


def instancia_unica(nome):
    """Cria um mutex com nome; devolve None se outro Clawd já estiver rodando."""
    if not WINDOWS:
        return True
    handle = _kernel32.CreateMutexW(None, False, nome)
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        return None
    return handle
