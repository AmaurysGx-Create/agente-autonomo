"""Preferencias del usuario (JSON en %APPDATA%\\GxKeybinds o ~/.config/gx_keybinds)."""
from __future__ import annotations

import json
import os
from pathlib import Path


def settings_path() -> Path:
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    folder = "GxKeybinds" if os.environ.get("APPDATA") else "gx_keybinds"
    return Path(base) / folder / "settings.json"


def load_settings(path: Path | None = None) -> dict:
    try:
        data = json.loads((path or settings_path()).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(data: dict, path: Path | None = None) -> None:
    p = path or settings_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass  # sin permisos de escritura: la preferencia solo vale para esta sesión
