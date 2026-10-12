"""Grabación de macros en vivo: convierte eventos con marca de tiempo en pasos."""
from __future__ import annotations

import time

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


def record_live(name: str, stop_key: str = "f12", record_moves: bool = False) -> Macro:
    """Graba teclado/ratón reales hasta pulsar `stop_key` (esa tecla no se graba)."""
    from pynput import keyboard, mouse

    rec = Recorder(record_moves=record_moves)
    stop = stop_key.lower()
    last_pos: list = [None]

    def kname(key) -> str:
        if isinstance(key, keyboard.KeyCode) and key.char:
            return key.char.lower()
        return getattr(key, "name", str(key))

    def on_press(key):
        n = kname(key)
        if n == stop:
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
        if last_pos[0] is not None:
            rec.add("move", x - last_pos[0][0], y - last_pos[0][1])
        last_pos[0] = (x, y)

    ml = mouse.Listener(on_click=on_click, on_move=on_move, on_scroll=on_scroll)
    ml.start()
    with keyboard.Listener(on_press=on_press, on_release=on_release) as kl:
        kl.join()
    ml.stop()
    return rec.to_macro(name)
