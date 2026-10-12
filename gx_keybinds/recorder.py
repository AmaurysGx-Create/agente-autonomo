"""Grabación de macros en vivo: convierte eventos con marca de tiempo en pasos."""
from __future__ import annotations

import time

from .keynames import name_from_pynput
from .model import Macro, Step


class Recorder:
    """Acumula eventos; `to_macro()` genera los pasos con las esperas intermedias.

    La lógica es pura (se alimenta con `add`), así se puede probar sin teclado real.
    """

    def __init__(self, record_moves: bool = False, min_wait_ms: float = 1.0):
        self.record_moves = record_moves
        self.min_wait_ms = min_wait_ms
        self.events: list[tuple[float, str, tuple]] = []  # (t, tipo, args)

    def add(self, kind: str, *args, t: float | None = None) -> None:
        if kind == "move" and not self.record_moves:
            return
        self.events.append((time.perf_counter() if t is None else t, kind, args))

    def to_macro(self, name: str, **kw) -> Macro:
        steps: list[Step] = []
        prev_t = self.events[0][0] if self.events else 0.0
        for t, kind, args in self.events:
            gap = (t - prev_t) * 1000
            prev_t = t
            if gap >= self.min_wait_ms and steps:
                if steps[-1].type == "wait":
                    steps[-1].ms += gap
                else:
                    steps.append(Step("wait", ms=round(gap, 1)))
            if kind == "key_down":
                steps.append(Step("down", key=args[0]))
            elif kind == "key_up":
                steps.append(Step("up", key=args[0]))
            elif kind == "mouse_down":
                steps.append(Step("down", key=f"mouse_{args[0]}"))
            elif kind == "mouse_up":
                steps.append(Step("up", key=f"mouse_{args[0]}"))
            elif kind == "scroll":
                steps.append(Step("scroll", dx=args[0], dy=args[1]))
            elif kind == "move":
                dx, dy = args
                if steps and steps[-1].type == "move":
                    steps[-1].dx += dx
                    steps[-1].dy += dy
                else:
                    steps.append(Step("move", dx=dx, dy=dy))
        for s in steps:
            if s.type == "wait":
                s.ms = round(s.ms, 1)
        m = Macro(name=name, steps=steps, **kw)
        m.validate()
        return m


class LiveRecorder:
    """Graba teclado/ratón reales en segundo plano; se detiene con `stop()` o `stop_key`."""

    def __init__(self, stop_key: str | None = "f12", record_moves: bool = False,
                 on_stop=None):
        self.rec = Recorder(record_moves=record_moves)
        self.stop_key = stop_key.lower() if stop_key else None
        self.on_stop = on_stop      # callback (hilo del listener) al terminar por stop_key
        self._listeners: list = []
        self._last_pos = None

    @property
    def active(self) -> bool:
        return bool(self._listeners)

    def start(self) -> None:
        from pynput import keyboard, mouse
        rec, stop = self.rec, self.stop_key

        kname = name_from_pynput

        def on_press(key):
            n = kname(key)
            if n == stop:
                self.stop()
                if self.on_stop:
                    self.on_stop()
                return False
            rec.add("key_down", n)

        def on_release(key):
            n = kname(key)
            if n != stop:
                rec.add("key_up", n)

        def on_click(x, y, button, pressed):
            rec.add("mouse_down" if pressed else "mouse_up", button.name)

        def on_scroll(x, y, dx, dy):
            rec.add("scroll", dx, dy)

        def on_move(x, y):
            if self._last_pos is not None:
                rec.add("move", x - self._last_pos[0], y - self._last_pos[1])
            self._last_pos = (x, y)

        self._listeners = [
            keyboard.Listener(on_press=on_press, on_release=on_release),
            mouse.Listener(on_click=on_click, on_move=on_move, on_scroll=on_scroll)]
        for l in self._listeners:
            l.start()

    def stop(self) -> None:
        for l in self._listeners:
            l.stop()
        self._listeners = []

    def wait(self) -> None:
        for l in list(self._listeners):
            l.join()

    def to_macro(self, name: str, **kw) -> Macro:
        return self.rec.to_macro(name, **kw)


def record_live(name: str, stop_key: str = "f12", record_moves: bool = False) -> Macro:
    """Graba hasta pulsar `stop_key` (esa tecla no se graba). Bloquea."""
    lr = LiveRecorder(stop_key=stop_key, record_moves=record_moves)
    lr.start()
    lr.wait()
    return lr.to_macro(name)
