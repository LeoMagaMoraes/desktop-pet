"""Acesso à API do Windows: DPI, área de trabalho, estilo da janela e instância única."""

import ctypes
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

SPI_GETWORKAREA = 0x30
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x80
WS_EX_APPWINDOW = 0x40000
ERROR_ALREADY_EXISTS = 183


@dataclass(frozen=True)
class Area:
    """Retângulo da tela sem a barra de tarefas. `base` é o topo da barra."""
    esquerda: int
    topo: int
    direita: int
    base: int


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


def estilo_ferramenta(janela):
    """Tira a janela do Alt+Tab e da barra de tarefas."""
    if not WINDOWS:
        return
    hwnd = _user32.GetParent(janela.winfo_id()) or janela.winfo_id()
    estilo = _user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    _user32.SetWindowLongW(hwnd, GWL_EXSTYLE, (estilo | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW)


def instancia_unica(nome):
    """Cria um mutex com nome; devolve None se outro Clawd já estiver rodando."""
    if not WINDOWS:
        return True
    handle = _kernel32.CreateMutexW(None, False, nome)
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        return None
    return handle
