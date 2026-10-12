"""Disparadores globales con pynput. Incluye tecla de pánico que detiene todo."""
from __future__ import annotations

from .engine import norm_key as _norm


def listen(manager, panic: str = "<f12>"):
    """Bloquea hasta que se pulse la tecla de pánico (que además detiene macros)."""
    from pynput import keyboard

    pressed: set[str] = set()
    hk_active: dict[str, bool] = {}
    hk_name: dict[str, str] = {}

    def canon(key) -> str:
        if isinstance(key, keyboard.KeyCode) and key.char:
            return key.char.lower()
        return f"<{getattr(key, 'name', str(key))}>"

    stop_flag = {"stop": False}

    def on_press(key):
        c = canon(key)
        pressed.add(c)
        if c == _norm(panic):
            manager.stop_all()
            stop_flag["stop"] = True
            return False
        name = manager.lookup(c)
        if name and not hk_active.get(c):
            hk_active[c] = True  # evita auto-repeat del SO
            hk_name[c] = name    # recordar la macro (el perfil puede cambiar antes de soltar)
            manager.press(name)

    def on_release(key):
        c = canon(key)
        pressed.discard(c)
        if hk_active.get(c):
            hk_active[c] = False
            name = hk_name.pop(c, None)
            if name:
                manager.release(name)

    with keyboard.Listener(on_press=on_press, on_release=on_release) as l:
        l.join()
