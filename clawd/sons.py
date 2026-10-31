"""Sonzinhos com o winsound, tocados numa thread pra não travar a animação."""

import threading
import time

try:
    import winsound
except ImportError:      # fora do Windows fica mudo
    winsound = None

# (frequência em Hz, duração em ms); frequência 0 = pausa
MELODIAS = {
    "fim": [(784, 90), (988, 90), (1175, 90), (1568, 200)],      # ta-da!
    "chamando": [(880, 120), (0, 90), (880, 120)],
    "ok": [(1047, 80), (1319, 140)],
    "triste": [(523, 160), (440, 160), (330, 320)],
}


def _tocar(notas):
    for freq, ms in notas:
        if freq:
            winsound.Beep(freq, ms)
        else:
            time.sleep(ms / 1000)


def tocar(nome):
    if winsound is None or nome not in MELODIAS:
        return
    threading.Thread(target=_tocar, args=(MELODIAS[nome],), daemon=True).start()
