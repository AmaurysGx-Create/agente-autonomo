"""Lógica pura del editor de pasos (sin tkinter, para poder probarla)."""
from __future__ import annotations

import copy

from .model import Macro, MacroError, Step

# tipo -> [(atributo, etiqueta, tipo de dato, valor por defecto)]
FIELDS: dict[str, list[tuple[str, str, str, object]]] = {
    "down":   [("key", "Tecla (a, space, mouse_left…)", "str", "")],
    "up":     [("key", "Tecla (a, space, mouse_left…)", "str", "")],
    "tap":    [("key", "Tecla", "str", ""), ("hold_ms", "Pulsada (ms)", "float", 20),
               ("ms", "Pausa después (ms)", "float", 0)],
    "click":  [("button", "Botón (left/right/middle)", "str", "left"), ("count", "Veces", "int", 1),
               ("hold_ms", "Pulsado (ms)", "float", 20), ("ms", "Pausa entre clics (ms)", "float", 0)],
    "move":   [("dx", "dx (relativo)", "int", 0), ("dy", "dy (relativo)", "int", 0)],
    "moveto": [("dx", "x (pantalla)", "int", 0), ("dy", "y (pantalla)", "int", 0)],
    "scroll": [("dx", "dx", "int", 0), ("dy", "dy (negativo = abajo)", "int", -1)],
    "wait":   [("ms", "Espera (ms)", "float", 100)],
    "text":   [("value", "Texto", "str", "")],
}


def build_step(type_: str, values: dict[str, str]) -> Step:
    """Crea un Step validado a partir de cadenas de un formulario."""
    if type_ not in FIELDS:
        raise MacroError(f"tipo de paso desconocido: {type_!r}")
    kw: dict = {}
    for attr, label, kind, default in FIELDS[type_]:
        raw = str(values.get(attr, default)).strip()
        if kind == "str":
            kw[attr] = raw if (raw or attr == "value") else str(default)
            if attr == "value":
                kw[attr] = str(values.get(attr, ""))   # el texto conserva espacios
            continue
        try:
            kw[attr] = int(raw) if kind == "int" else float(raw)
        except ValueError:
            raise MacroError(f"«{label}» debe ser un número") from None
    s = Step(type_, **kw)
    s.validate()
    return s


def step_values(step: Step) -> dict[str, str]:
    return {attr: str(getattr(step, attr)) for attr, *_ in FIELDS[step.type]}


def describe(s: Step) -> str:
    t = s.type
    if t in ("down", "up"):
        return f"{'Pulsar' if t == 'down' else 'Soltar'} {s.key}"
    if t == "tap":
        return f"Tocar {s.key} ({s.hold_ms:g} ms)" + (f", pausa {s.ms:g} ms" if s.ms else "")
    if t == "click":
        return f"Clic {s.button} ×{s.count}"
    if t == "move":
        return f"Mover ({s.dx:+d}, {s.dy:+d})"
    if t == "moveto":
        return f"Ir a ({s.dx}, {s.dy})"
    if t == "scroll":
        return f"Rueda ({s.dx}, {s.dy})"
    if t == "wait":
        return f"Esperar {s.ms:g} ms"
    return f"Escribir «{s.value}»"


def duration_ms(m: Macro) -> float:
    """Duración aproximada de una pasada (esperas + pulsaciones)."""
    total = 0.0
    for s in m.steps:
        if s.type == "wait":
            total += s.ms
        elif s.type == "tap":
            total += s.hold_ms + s.ms
        elif s.type == "click":
            total += s.count * (s.hold_ms + s.ms)
    return total


class StepEditor:
    """Edita la lista de pasos de una macro con deshacer/rehacer."""

    def __init__(self, macro: Macro):
        self.macro = macro
        self._undo: list[list[Step]] = []
        self._redo: list[list[Step]] = []

    @property
    def steps(self) -> list[Step]:
        return self.macro.steps

    def _snap(self) -> None:
        self._undo.append(copy.deepcopy(self.macro.steps))
        self._redo.clear()
        del self._undo[:-100]

    def _fix_loop_from(self) -> None:
        self.macro.loop_from = min(self.macro.loop_from, max(len(self.steps) - 1, 0))

    def add(self, step: Step, index: int | None = None) -> int:
        self._snap()
        i = len(self.steps) if index is None else max(0, min(index, len(self.steps)))
        self.steps.insert(i, step)
        return i

    def replace(self, index: int, step: Step) -> None:
        self._snap()
        self.steps[index] = step

    def delete(self, indices: list[int]) -> None:
        if not indices:
            return
        self._snap()
        for i in sorted(set(indices), reverse=True):
            del self.steps[i]
        self._fix_loop_from()

    def duplicate(self, indices: list[int]) -> list[int]:
        if not indices:
            return []
        self._snap()
        idx = sorted(set(indices))
        copies = [copy.deepcopy(self.steps[i]) for i in idx]
        pos = idx[-1] + 1
        self.steps[pos:pos] = copies
        return list(range(pos, pos + len(copies)))

    def move(self, indices: list[int], delta: int) -> list[int]:
        """Mueve un bloque de pasos `delta` posiciones (-1 sube, +1 baja)."""
        idx = sorted(set(indices))
        if not idx or delta == 0:
            return idx
        if idx[0] + delta < 0 or idx[-1] + delta >= len(self.steps):
            return idx
        self._snap()
        block = [self.steps[i] for i in idx]
        for i in reversed(idx):
            del self.steps[i]
        start = idx[0] + delta
        self.steps[start:start] = block
        return list(range(start, start + len(block)))

    def set_loop_from(self, index: int) -> None:
        self.macro.loop_from = max(0, min(index, max(len(self.steps) - 1, 0)))

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(copy.deepcopy(self.macro.steps))
        self.macro.steps[:] = self._undo.pop()
        self._fix_loop_from()
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(copy.deepcopy(self.macro.steps))
        self.macro.steps[:] = self._redo.pop()
        return True
