"""Distribución del teclado en pantalla (lógica pura, sin tkinter).

Los nombres de tecla son los mismos que usan los backends y el importador .amc.
"""
from __future__ import annotations

from typing import Iterable

from .model import Step

# Una fila = lista de (etiqueta, tecla, ancho) o un float (hueco). Medidas en "teclas" (1.0 = tecla estándar).
_MAIN_ROWS: list[list] = [
    [("Esc", "esc", 1), 1, ("F1", "f1", 1), ("F2", "f2", 1), ("F3", "f3", 1), ("F4", "f4", 1), 0.5,
     ("F5", "f5", 1), ("F6", "f6", 1), ("F7", "f7", 1), ("F8", "f8", 1), 0.5,
     ("F9", "f9", 1), ("F10", "f10", 1), ("F11", "f11", 1), ("F12", "f12", 1)],
    [("`", "`", 1)] + [(c, c, 1) for c in "1234567890-="] + [("Retroceso", "backspace", 2)],
    [("Tab", "tab", 1.5)] + [(c.upper(), c, 1) for c in "qwertyuiop"] +
    [("[", "[", 1), ("]", "]", 1), ("\\", "\\", 1.5)],
    [("Bloq", "caps_lock", 1.75)] + [(c.upper(), c, 1) for c in "asdfghjkl"] +
    [(";", ";", 1), ("'", "'", 1), ("Enter", "enter", 2.25)],
    [("Shift", "shift", 2.25)] + [(c.upper(), c, 1) for c in "zxcvbnm"] +
    [(",", ",", 1), (".", ".", 1), ("/", "/", 1), ("Shift", "shift_r", 2.75)],
    [("Ctrl", "ctrl_l", 1.25), ("Win", "cmd", 1.25), ("Alt", "alt_l", 1.25), ("Espacio", "space", 6.25),
     ("Alt", "alt_r", 1.25), ("Win", "cmd_r", 1.25), ("Menú", "menu", 1.25), ("Ctrl", "ctrl_r", 1.25)],
]
_NAV_X = 15.5   # columna donde empieza el bloque de navegación
_NAV: list[tuple[str, str, float, float]] = [   # (etiqueta, tecla, x, y) en teclas
    ("Imp", "print_screen", _NAV_X, 0), ("ScrLk", "scroll_lock", _NAV_X + 1, 0), ("Pause", "pause", _NAV_X + 2, 0),
    ("Ins", "insert", _NAV_X, 1.5), ("Home", "home", _NAV_X + 1, 1.5), ("PgUp", "page_up", _NAV_X + 2, 1.5),
    ("Supr", "delete", _NAV_X, 2.5), ("Fin", "end", _NAV_X + 1, 2.5), ("PgDn", "page_down", _NAV_X + 2, 2.5),
    ("↑", "up", _NAV_X + 1, 4.5),
    ("←", "left", _NAV_X, 5.5), ("↓", "down", _NAV_X + 1, 5.5), ("→", "right", _NAV_X + 2, 5.5),
]
# Fila de ratón bajo el teclado: (etiqueta, id, ancho)
MOUSE_KEYS = [("Clic izq.", "mouse_left", 2), ("Clic medio", "mouse_middle", 2), ("Clic der.", "mouse_right", 2),
              ("Rueda arriba", "wheel_up", 2), ("Rueda abajo", "wheel_down", 2)]
_NUM_X = _NAV_X + 3.5
_NUMPAD: list[tuple[str, str, float, float, float, float]] = [   # (etiqueta, tecla, x, y, ancho, alto)
    ("Num", "num_lock", _NUM_X, 1.5, 1, 1), ("/", "num_divide", _NUM_X + 1, 1.5, 1, 1),
    ("*", "num_multiply", _NUM_X + 2, 1.5, 1, 1), ("-", "num_subtract", _NUM_X + 3, 1.5, 1, 1),
    ("7", "num7", _NUM_X, 2.5, 1, 1), ("8", "num8", _NUM_X + 1, 2.5, 1, 1), ("9", "num9", _NUM_X + 2, 2.5, 1, 1),
    ("+", "num_add", _NUM_X + 3, 2.5, 1, 2),
    ("4", "num4", _NUM_X, 3.5, 1, 1), ("5", "num5", _NUM_X + 1, 3.5, 1, 1), ("6", "num6", _NUM_X + 2, 3.5, 1, 1),
    ("1", "num1", _NUM_X, 4.5, 1, 1), ("2", "num2", _NUM_X + 1, 4.5, 1, 1), ("3", "num3", _NUM_X + 2, 4.5, 1, 1),
    ("Intro", "num_enter", _NUM_X + 3, 4.5, 1, 2),
    ("0", "num0", _NUM_X, 5.5, 2, 1), (".", "num_decimal", _NUM_X + 2, 5.5, 1, 1),
]
MOUSE_ROW_Y = 7.0
WIDTH_KEYS = 23.0
HEIGHT_KEYS = 8.0


def _items() -> list[tuple[str, str, float, float, float, float]]:
    out = []
    for r, row in enumerate(_MAIN_ROWS):
        x, y = 0.0, r + (0.5 if r else 0)   # separación entre la fila de F y el resto
        for it in row:
            if isinstance(it, (int, float)):
                x += it
                continue
            label, key, w = it
            out.append((label, key, x, y, w, 1.0))
            x += w
    out += [(l, k, x, y, 1.0, 1.0) for l, k, x, y in _NAV]
    out += _NUMPAD
    x = 0.0
    for label, key, w in MOUSE_KEYS:
        out.append((label, key, x, MOUSE_ROW_Y, w, 1.0))
        x += w
    return out


def key_rects(unit: int = 36, gap: int = 3) -> list[tuple[str, str, int, int, int, int]]:
    """[(etiqueta, tecla, x, y, ancho, alto)] en píxeles."""
    return [(label, key, round(x * unit), round(y * unit), round(w * unit) - gap, round(h * unit) - gap)
            for label, key, x, y, w, h in _items()]


def all_keys() -> list[str]:
    return [k for _, k, *_ in _items()]


def step_for_key(key: str, mode: str = "tap", hold_ms: float = 20) -> Step:
    """Paso a insertar al pulsar una tecla del teclado en pantalla. mode: tap | down | up."""
    if key in ("wheel_up", "wheel_down"):
        return Step("scroll", dy=1 if key == "wheel_up" else -1)
    if key.startswith("mouse_"):
        if mode == "tap":
            return Step("click", button=key[len("mouse_"):], hold_ms=hold_ms)
        return Step(mode, key=key)
    if mode == "tap":
        return Step("tap", key=key, hold_ms=hold_ms)
    return Step(mode, key=key)


def keys_used(steps: Iterable[Step]) -> set[str]:
    """Teclas del teclado en pantalla que usan estos pasos (para resaltarlas)."""
    used: set[str] = set()
    for s in steps:
        if s.type in ("down", "up", "tap") and s.key:
            used.add(s.key)
        elif s.type == "click":
            used.add(f"mouse_{s.button}")
        elif s.type == "scroll" and s.dy:
            used.add("wheel_up" if s.dy > 0 else "wheel_down")
    return used
