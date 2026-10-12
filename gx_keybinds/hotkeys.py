"""Disparadores globales con pynput. Incluye tecla de pánico que detiene todo."""
from __future__ import annotations

import threading
from typing import Callable

from .engine import norm_key as _norm


class HotkeyListener:
    """Escucha teclas globales y las enruta a `manager` (lookup/press/release/stop_all).

    - La tecla de pánico detiene todas las macros y llama a `on_panic` (si se da).
    - `manager` puede cambiar de contenido entre pulsaciones (perfiles): se consulta en cada tecla.
    """

    def __init__(self, manager, panic: str = "<f12>", on_panic: Callable[[], None] | None = None,
                 stop_on_panic: bool = False):
        self.manager, self.panic, self.on_panic = manager, _norm(panic), on_panic
        self.stop_on_panic = stop_on_panic
        self._listener = None
        self._active: dict[str, str] = {}   # tecla -> macro que disparó (hasta soltarla)

    @property
    def running(self) -> bool:
        return self._listener is not None and self._listener.is_alive()

    def start(self) -> None:
        from pynput import keyboard
        if self.running:
            return

        def canon(key) -> str:
            if isinstance(key, keyboard.KeyCode) and key.char:
                return key.char.lower()
            return f"<{getattr(key, 'name', str(key))}>"

        def on_press(key):
            c = canon(key)
            if c == self.panic:
                self.manager.stop_all()
                self._active.clear()
                if self.on_panic:
                    self.on_panic()
                return False if self.stop_on_panic else None
            name = self.manager.lookup(c)
            if name and c not in self._active:   # ignora el auto-repeat del sistema
                self._active[c] = name
                self.manager.press(name)

        def on_release(key):
            c = canon(key)
            name = self._active.pop(c, None)
            if name:
                self.manager.release(name)

        self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None
        self.manager.stop_all()
        self._active.clear()

    def join(self) -> None:
        if self._listener:
            self._listener.join()


def listen(manager, panic: str = "<f12>"):
    """Bloquea hasta que se pulse la tecla de pánico (que además detiene macros)."""
    hl = HotkeyListener(manager, panic=panic, stop_on_panic=True)
    hl.start()
    try:
        hl.join()
    finally:
        hl._listener = None
