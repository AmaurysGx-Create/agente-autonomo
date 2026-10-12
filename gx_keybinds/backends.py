"""Backends de entrada: real (pynput) y de simulación (solo registra)."""
from __future__ import annotations

from abc import ABC, abstractmethod


class Backend(ABC):
    @abstractmethod
    def key_down(self, key: str) -> None: ...
    @abstractmethod
    def key_up(self, key: str) -> None: ...
    @abstractmethod
    def mouse_down(self, button: str) -> None: ...
    @abstractmethod
    def mouse_up(self, button: str) -> None: ...
    @abstractmethod
    def mouse_move(self, dx: int, dy: int) -> None: ...
    @abstractmethod
    def mouse_moveto(self, x: int, y: int) -> None: ...
    @abstractmethod
    def scroll(self, dx: int, dy: int) -> None: ...
    @abstractmethod
    def type_text(self, text: str) -> None: ...


class DryRunBackend(Backend):
    """No envía nada al sistema; guarda los eventos (útil para tests y --dry-run)."""

    def __init__(self, echo: bool = False):
        self.events: list[tuple] = []
        self.times: list[float] = []     # segundos desde el primer evento (para "Probar")
        self._t0: float | None = None
        self.echo = echo

    def _rec(self, *ev):
        import time
        now = time.perf_counter()
        self._t0 = self._t0 if self._t0 is not None else now
        self.times.append(now - self._t0)
        self.events.append(ev)
        if self.echo:
            print("[dry-run]", *ev)

    def key_down(self, key): self._rec("key_down", key)
    def key_up(self, key): self._rec("key_up", key)
    def mouse_down(self, button): self._rec("mouse_down", button)
    def mouse_up(self, button): self._rec("mouse_up", button)
    def mouse_move(self, dx, dy): self._rec("mouse_move", dx, dy)
    def mouse_moveto(self, x, y): self._rec("mouse_moveto", x, y)
    def scroll(self, dx, dy): self._rec("scroll", dx, dy)
    def type_text(self, text): self._rec("type_text", text)


class PynputBackend(Backend):
    def __init__(self):
        from pynput import keyboard, mouse  # import tardío: requiere entorno gráfico
        self._kb = keyboard.Controller()
        self._ms = mouse.Controller()
        self._Key = keyboard.Key
        self._Button = mouse.Button

    def _key(self, name: str):
        if len(name) == 1:
            return name
        from .keynames import NUMPAD, numpad_vk
        if name in NUMPAD:
            from pynput import keyboard
            return keyboard.KeyCode.from_vk(numpad_vk(name))
        if name == "num_enter":
            return self._Key.enter
        try:
            return getattr(self._Key, name.lower())
        except AttributeError:
            raise ValueError(f"tecla desconocida: {name!r}") from None

    def key_down(self, key): self._kb.press(self._key(key))
    def key_up(self, key): self._kb.release(self._key(key))
    def mouse_down(self, button): self._ms.press(getattr(self._Button, button))
    def mouse_up(self, button): self._ms.release(getattr(self._Button, button))
    def mouse_move(self, dx, dy): self._ms.move(dx, dy)
    def mouse_moveto(self, x, y): self._ms.position = (x, y)
    def scroll(self, dx, dy): self._ms.scroll(dx, dy)
    def type_text(self, text): self._kb.type(text)
