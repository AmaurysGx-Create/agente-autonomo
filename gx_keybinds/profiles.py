"""Perfiles por programa: cada perfil agrupa macros y se activa según la ventana en primer plano.

Formato JSON:
{"profiles": [
  {"name": "Notepad", "process": "notepad.exe", "title_contains": "bloc",
   "macros": [ {macro...} ],            # macros en línea
   "macros_file": "otro.json|x.amc",    # y/o macros desde un archivo (ruta relativa al perfil)
   "bind": {"Nombre macro": "f6"}},     # asigna/cambia la tecla de activación
  {"name": "Global"}                    # sin process/title => perfil por defecto (fallback)
]}
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .active_window import Window, get_active_window
from .backends import Backend
from .engine import Manager, norm_key
from .model import Macro, MacroError, load_macros


@dataclass
class Profile:
    name: str
    macros: list[Macro] = field(default_factory=list)
    process: str | None = None
    title_contains: str | None = None

    @property
    def is_default(self) -> bool:
        return not self.process and not self.title_contains

    def matches(self, w: Window | None) -> bool:
        if self.is_default or w is None:
            return False
        if self.process and self.process.lower() != w.process.lower():
            return False
        if self.title_contains and self.title_contains.lower() not in w.title.lower():
            return False
        return True


class ProfileSet:
    def __init__(self, profiles: list[Profile]):
        names = [p.name for p in profiles]
        if len(set(names)) != len(names):
            raise MacroError("nombres de perfil duplicados")
        self.profiles = profiles

    def select(self, w: Window | None) -> Profile | None:
        """El primer perfil específico que coincide; si no, el perfil por defecto."""
        for p in self.profiles:
            if p.matches(w):
                return p
        return next((p for p in self.profiles if p.is_default), None)

    def get(self, name: str) -> Profile:
        for p in self.profiles:
            if p.name == name:
                return p
        raise KeyError(name)


def is_profile_file(path: str | Path) -> bool:
    if not str(path).lower().endswith(".json"):
        return False
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(d, dict) and "profiles" in d


def _profile_from_dict(d: dict, base: Path) -> Profile:
    if not isinstance(d, dict) or not d.get("name"):
        raise MacroError("cada perfil necesita 'name'")
    macros = [Macro.from_dict(m) for m in d.get("macros", [])]
    if d.get("macros_file"):
        target = (base / d["macros_file"]).resolve()
        if not target.is_relative_to(base.resolve()):
            raise MacroError(f"macros_file fuera de la carpeta del perfil: {d['macros_file']}")
        macros += load_macros(target)
    bind = d.get("bind", {})
    names = [m.name for m in macros]
    if len(set(names)) != len(names):
        raise MacroError(f"perfil {d['name']!r}: macros con nombre repetido")
    for mname, key in bind.items():
        hit = [m for m in macros if m.name == mname]
        if not hit:
            raise MacroError(f"perfil {d['name']!r}: bind a macro inexistente {mname!r}")
        hit[0].trigger = key
    return Profile(d["name"], macros, d.get("process"), d.get("title_contains"))


def load_profiles(path: str | Path) -> ProfileSet:
    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        items = data["profiles"]
    except (KeyError, TypeError, ValueError) as e:
        raise MacroError(f"archivo de perfiles inválido: {e}") from e
    return ProfileSet([_profile_from_dict(d, p.parent) for d in items])


def save_profiles(path: str | Path, pset: ProfileSet) -> None:
    out = []
    for p in pset.profiles:
        d: dict = {"name": p.name}
        if p.process:
            d["process"] = p.process
        if p.title_contains:
            d["title_contains"] = p.title_contains
        d["macros"] = [m.to_dict() for m in p.macros]
        out.append(d)
    Path(path).write_text(json.dumps({"profiles": out}, indent=2, ensure_ascii=False), encoding="utf-8")


class ProfileManager:
    """Cambia automáticamente de perfil según la ventana activa.

    Al cambiar de perfil se detienen todas las macros del anterior (soltando sus teclas).
    Misma interfaz que Manager (lookup/press/release/stop_all) para usarlo con hotkeys.listen.
    """

    def __init__(self, pset: ProfileSet, backend: Backend,
                 get_window: Callable[[], Window | None] = get_active_window,
                 poll: float = 0.3, on_change: Callable[[Profile | None], None] | None = None):
        self.pset, self.backend = pset, backend
        self.get_window, self.poll, self.on_change = get_window, poll, on_change
        self.current: Profile | None = None
        self._mgr: Manager | None = None
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.refresh(force=True)

    def refresh(self, force: bool = False) -> bool:
        """Re-evalúa la ventana activa. True si el perfil cambió."""
        target = self.pset.select(self.get_window())
        with self._lock:
            if not force and target is self.current:
                return False
            if self._mgr:
                self._mgr.stop_all()
            self.current = target
            self._mgr = Manager(target.macros, self.backend) if target else None
        if self.on_change:
            self.on_change(target)
        return True

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="profiles")
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.wait(self.poll):
            try:
                self.refresh()
            except Exception:
                pass  # una lectura fallida de ventana no debe tumbar el hilo

    def close(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        self.stop_all()

    # --- interfaz tipo Manager ---
    def lookup(self, trigger: str) -> str | None:
        with self._lock:
            return self._mgr.lookup(trigger) if self._mgr else None

    def press(self, name: str) -> None:
        with self._lock:
            if self._mgr and name in self._mgr.runners:
                self._mgr.press(name)

    def release(self, name: str) -> None:
        with self._lock:
            if self._mgr and name in self._mgr.runners:
                self._mgr.release(name)

    def stop_all(self) -> None:
        with self._lock:
            if self._mgr:
                self._mgr.stop_all()
