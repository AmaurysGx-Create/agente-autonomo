"""Nombres de tecla comunes: numpad (num0…num9, num_add…) y conversión desde/hacia pynput."""
from __future__ import annotations

import sys

# vk de Windows (VK_NUMPAD0=0x60 …)  y keysyms de X11 (XK_KP_0=0xFFB0 …)
_WIN_VK = {**{f"num{i}": 0x60 + i for i in range(10)},
           "num_multiply": 0x6A, "num_add": 0x6B, "num_subtract": 0x6D,
           "num_decimal": 0x6E, "num_divide": 0x6F}
_X11_SYM = {**{f"num{i}": 0xFFB0 + i for i in range(10)},
            "num_multiply": 0xFFAA, "num_add": 0xFFAB, "num_subtract": 0xFFAD,
            "num_decimal": 0xFFAE, "num_divide": 0xFFAF}
NUMPAD = {k: None for k in _WIN_VK}   # solo los nombres válidos


def numpad_vk(name: str) -> int | None:
    """Código virtual (Windows) o keysym (X11) de una tecla del teclado numérico."""
    table = _WIN_VK if sys.platform == "win32" else _X11_SYM
    return table.get(name)


def name_from_pynput(key) -> str:
    """Nombre estable de una tecla de pynput (distingue el teclado numérico del bloque principal)."""
    vk = getattr(key, "vk", None)
    if vk is not None:
        table = _WIN_VK if sys.platform == "win32" else _X11_SYM
        for n, v in table.items():
            if v == vk:
                return n
    char = getattr(key, "char", None)
    if char:
        return char.lower()
    return getattr(key, "name", str(key))
