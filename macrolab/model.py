"""Modelo de datos de macros y (de)serialización JSON."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

STEP_TYPES = {"down", "up", "tap", "click", "move", "wait", "text"}
TRIGGER_MODES = {"toggle", "hold", "once"}


class MacroError(ValueError):
    pass


@dataclass
class Step:
    type: str
    key: str | None = None      # down/up/tap
    button: str = "left"        # click
    count: int = 1              # click
    dx: int = 0                 # move (relativo)
    dy: int = 0
    ms: float = 0               # wait / pausa tras tap
    hold_ms: float = 20         # tap: tiempo pulsada
    value: str = ""             # text

    def validate(self) -> None:
        if self.type not in STEP_TYPES:
            raise MacroError(f"tipo de paso desconocido: {self.type!r}")
        if self.type in {"down", "up", "tap"} and not self.key:
            raise MacroError(f"el paso '{self.type}' requiere 'key'")
        if self.type == "click" and self.button not in {"left", "right", "middle"}:
            raise MacroError(f"botón inválido: {self.button!r}")
        if self.ms < 0 or self.hold_ms < 0 or self.count < 1:
            raise MacroError("ms/hold_ms no pueden ser negativos y count >= 1")


@dataclass
class Macro:
    name: str
    steps: list[Step] = field(default_factory=list)
    trigger: str | None = None   # p. ej. "f6", "<ctrl>+<alt>+m"
    mode: str = "toggle"         # toggle | hold | once
    loop: int | bool = False     # False=1 vez, True=infinito, N=N veces
    description: str = ""

    def validate(self) -> None:
        if not self.name:
            raise MacroError("la macro necesita 'name'")
        if self.mode not in TRIGGER_MODES:
            raise MacroError(f"modo inválido: {self.mode!r}")
        for s in self.steps:
            s.validate()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Macro":
        try:
            steps = [Step(**s) for s in d.get("steps", [])]
            m = cls(
                name=d["name"], steps=steps, trigger=d.get("trigger"),
                mode=d.get("mode", "toggle"), loop=d.get("loop", False),
                description=d.get("description", ""),
            )
        except (KeyError, TypeError) as e:
            raise MacroError(f"macro mal formada: {e}") from e
        m.validate()
        return m

    def to_dict(self) -> dict[str, Any]:
        defaults = Step("x")
        steps = []
        for s in self.steps:
            d = {"type": s.type}
            for k, v in s.__dict__.items():
                if k != "type" and v != getattr(defaults, k):
                    d[k] = v
            steps.append(d)
        return {"name": self.name, "description": self.description,
                "trigger": self.trigger, "mode": self.mode,
                "loop": self.loop, "steps": steps}


def load_macros(path: str | Path) -> list[Macro]:
    """Carga un .json con una macro o una lista de macros."""
    if str(path).lower().endswith(".amc"):
        from .importers import load_amc
        return load_amc(path)[0]
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data["macros"] if isinstance(data, dict) and "macros" in data else data
    if isinstance(items, dict):
        items = [items]
    return [Macro.from_dict(d) for d in items]


def save_macros(path: str | Path, macros: list[Macro]) -> None:
    Path(path).write_text(
        json.dumps({"macros": [m.to_dict() for m in macros]}, indent=2, ensure_ascii=False),
        encoding="utf-8")
