"""Motor de ejecución: corre macros en hilos, con parada segura."""
from __future__ import annotations

import threading
import time

from .backends import Backend
from .model import Macro, Step


class Runner:
    """Ejecuta una macro; `stop()` la detiene y suelta todo lo que quedó pulsado."""

    def __init__(self, macro: Macro, backend: Backend):
        self.macro = macro
        self.backend = backend
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._held_keys: set[str] = set()
        self._held_buttons: set[str] = set()

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self.run, daemon=True, name=self.macro.name)
        self._thread.start()

    def stop(self, join: bool = True) -> None:
        self._stop.set()
        if join and self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=2)

    def run(self) -> None:
        loop = self.macro.loop
        n = 0
        try:
            while not self._stop.is_set():
                start = self.macro.loop_from if n > 0 else 0
                for step in self.macro.steps[start:]:
                    if self._stop.is_set():
                        return
                    self._exec(step)
                n += 1
                if loop is False or (loop is not True and n >= int(loop)):
                    return
                if not self.macro.steps:
                    return
        finally:
            self._release_all()

    def _sleep(self, ms: float) -> None:
        if ms <= 0:
            return
        end = time.perf_counter() + ms / 1000
        # Evento para esperas largas, espera activa corta para precisión.
        while not self._stop.is_set():
            left = end - time.perf_counter()
            if left <= 0:
                return
            if left > 0.003:
                self._stop.wait(left - 0.002)

    def _exec(self, s: Step) -> None:
        b = self.backend
        if s.type in ("down", "up") and s.key.startswith("mouse_"):
            btn = s.key[len("mouse_"):]  # lo que graba el recorder
            if s.type == "down":
                b.mouse_down(btn); self._held_buttons.add(btn)
            else:
                b.mouse_up(btn); self._held_buttons.discard(btn)
        elif s.type == "down":
            b.key_down(s.key); self._held_keys.add(s.key)
        elif s.type == "up":
            b.key_up(s.key); self._held_keys.discard(s.key)
        elif s.type == "tap":
            b.key_down(s.key); self._held_keys.add(s.key)
            self._sleep(s.hold_ms)
            b.key_up(s.key); self._held_keys.discard(s.key)
            self._sleep(s.ms)
        elif s.type == "click":
            for _ in range(s.count):
                b.mouse_down(s.button); self._held_buttons.add(s.button)
                self._sleep(s.hold_ms)
                b.mouse_up(s.button); self._held_buttons.discard(s.button)
                self._sleep(s.ms)
        elif s.type == "move":
            b.mouse_move(s.dx, s.dy)
        elif s.type == "moveto":
            b.mouse_moveto(s.dx, s.dy)
        elif s.type == "scroll":
            b.scroll(s.dx, s.dy)
        elif s.type == "wait":
            self._sleep(s.ms)
        elif s.type == "text":
            b.type_text(s.value)

    def _release_all(self) -> None:
        for k in list(self._held_keys):
            self.backend.key_up(k)
        for btn in list(self._held_buttons):
            self.backend.mouse_up(btn)
        self._held_keys.clear()
        self._held_buttons.clear()


class Manager:
    """Gestiona varias macros y su ciclo de vida según el modo del disparador."""

    def __init__(self, macros: list[Macro], backend: Backend):
        self.backend = backend
        self.runners = {m.name: Runner(m, backend) for m in macros}

    def press(self, name: str) -> None:
        r = self.runners[name]
        mode = r.macro.mode
        if mode == "toggle":
            r.stop() if r.running else r.start()
        elif mode in ("hold", "once"):
            r.start()

    def release(self, name: str) -> None:
        r = self.runners[name]
        if r.macro.mode == "hold":
            r.stop()

    def stop_all(self) -> None:
        for r in self.runners.values():
            r.stop()
