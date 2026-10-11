"""Disparadores globales con pynput. Incluye tecla de pánico que detiene todo."""
from __future__ import annotations

from .engine import Manager


def _norm(k: str) -> str:
    k = k.lower()
    return k if "<" in k or len(k) == 1 else f"<{k}>"


def listen(manager: Manager, panic: str = "<f12>"):
    """Bloquea hasta que se pulse la tecla de pánico (que además detiene macros)."""
    from pynput import keyboard

    done = keyboard.Listener  # noqa: F841 (solo para claridad del import)
    triggers = {}
    for name, r in manager.runners.items():
        if r.macro.trigger:
            triggers[_norm(r.macro.trigger)] = name

    pressed: set[str] = set()
    hk_active: dict[str, bool] = {}

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
        if c in triggers and not hk_active.get(c):
            hk_active[c] = True  # evita auto-repeat del SO
            manager.press(triggers[c])

    def on_release(key):
        c = canon(key)
        pressed.discard(c)
        if c in triggers:
            hk_active[c] = False
            manager.release(triggers[c])

    with keyboard.Listener(on_press=on_press, on_release=on_release) as l:
        l.join()
