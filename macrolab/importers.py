"""Importa macros en formato .amc (XML con script de texto) a macros de MacroLab.

Seguridad: el archivo se trata solo como datos. Se rechazan DOCTYPE/ENTITY (XML bombs),
solo se aceptan las instrucciones KeyDown/KeyUp/Delay; cualquier otra línea se omite y
se informa en `warnings`. Nunca se ejecuta código del archivo.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .model import Macro, MacroError, Step

MAX_BYTES = 1_000_000

# Códigos USB HID (Keyboard/Keypad page) -> nombre de tecla de MacroLab/pynput.
_HID: dict[int, str] = {}
for i, c in enumerate("abcdefghijklmnopqrstuvwxyz"):
    _HID[4 + i] = c
for i, c in enumerate("1234567890"):
    _HID[30 + i] = c
_HID.update({40: "enter", 41: "esc", 42: "backspace", 43: "tab", 44: "space",
             57: "caps_lock", 70: "print_screen", 71: "scroll_lock", 72: "pause",
             73: "insert", 74: "home", 75: "page_up", 76: "delete", 77: "end",
             78: "page_down", 79: "right", 80: "left", 81: "down", 82: "up",
             224: "ctrl_l", 225: "shift", 226: "alt_l", 227: "cmd",
             228: "ctrl_r", 229: "shift_r", 230: "alt_r", 231: "cmd_r"})
for i in range(12):
    _HID[58 + i] = f"f{i + 1}"
_PUNCT = {45: "-", 46: "=", 47: "[", 48: "]", 49: "\\", 51: ";", 52: "'",
          53: "`", 54: ",", 55: ".", 56: "/"}
_HID.update(_PUNCT)

_LINE = re.compile(
    r"^(KeyDown|KeyUp)\s+(\d+)(?:\s+\d+)?$"            # 1,2: tecla
    r"|^Delay\s+(\d+(?:\.\d+)?)\s*(?:ms)?$"           # 3: espera
    r"|^(LeftDown)(?:\s+\d+)?$"                          # 4: botón izq. (visto en muestras)
    r"|^MoveR\s+(-?\d+)\s+(-?\d+)$"                    # 5,6: movimiento relativo
    r"|^Goto\s+(\d+)$"
    r"|^WheelDown\s+(\d+)$", re.I)                      # 8: rueda hacia abajo (visto en muestras)                           # 7: salto a la línea N (1-based)


def parse_syntax(text: str, warnings: list[str]) -> tuple[list[Step], int | None]:
    """Devuelve (pasos, loop_from). `Goto N` final => bucle que reinicia en la línea N."""
    steps: list[Step] = []
    line_start: dict[int, int] = {}   # nº de línea -> índice de paso
    loop_from: int | None = None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        line_start[n] = len(steps)
        m = _LINE.match(line)
        if not m:
            warnings.append(f"línea {n} no soportada, omitida: {line[:40]!r}")
            continue
        if m.group(3) is not None:
            steps.append(Step("wait", ms=float(m.group(3))))
            continue
        if m.group(4):
            steps.append(Step("down", key="mouse_left"))
            continue
        if m.group(5) is not None:
            steps.append(Step("move", dx=int(m.group(5)), dy=int(m.group(6))))
            continue
        if m.group(8) is not None:
            steps.append(Step("scroll", dy=-int(m.group(8))))  # abajo = negativo
            continue
        if m.group(7) is not None:
            target = int(m.group(7))
            if target in line_start and line_start[target] < len(steps):
                loop_from = line_start[target]
            else:
                warnings.append(f"línea {n}: Goto {target} no soportado, omitido")
            continue
        code = int(m.group(2))
        key = _HID.get(code)
        if key is None:
            warnings.append(f"línea {n}: código de tecla {code} desconocido, omitida")
            continue
        steps.append(Step("down" if m.group(1).lower() == "keydown" else "up", key=key))
    return steps, loop_from


def load_amc(path: str | Path) -> tuple[list[Macro], list[str]]:
    p = Path(path)
    if p.stat().st_size > MAX_BYTES:
        raise MacroError("archivo demasiado grande")
    raw = p.read_bytes()
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise MacroError("XML con DOCTYPE/ENTITY rechazado por seguridad")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        raise MacroError(f"XML inválido: {e}") from e

    warnings: list[str] = []
    macros: list[Macro] = []
    for node in root.iter("DefaultMacro"):
        name = (node.findtext("Major") or p.stem).strip()
        steps, loop_from = parse_syntax(node.findtext("KeyDown/Syntax") or "", warnings)
        if (node.findtext("KeyUp/Syntax") or "").strip():
            warnings.append("la sección KeyUp (al soltar la tecla) no está soportada todavía")
        repeat = (node.findtext("GUIOption/RepeatType") or "0").strip()
        looping = loop_from is not None
        if repeat not in ("0", "1"):
            warnings.append(f"RepeatType={repeat} no soportado; se ejecuta una vez")
        desc = (node.findtext("Description") or "").strip()
        software = (node.findtext("Software") or "").strip()
        if software:
            desc = f"[{software}] {desc}"
        m = Macro(name=name, steps=steps, description=desc,
                  mode="hold" if looping else "once", loop=looping,
                  loop_from=loop_from or 0)
        m.validate()
        macros.append(m)
    if not macros:
        raise MacroError("no se encontró ninguna <DefaultMacro> en el archivo")
    return macros, warnings
