"""Ajustes de Windows para mejorar la respuesta del teclado/ratón. Todos son reversibles.

Qué hace cada uno (y qué NO hace):
- Repetición rápida de teclas: retardo mínimo (250 ms) y velocidad máxima (~30/s) al MANTENER una tecla.
  No cambia la latencia de una pulsación simple.
- Ratón sin aceleración: desactiva «Mejorar la precisión del puntero» (movimiento 1:1).
- Temporizador de 1 ms: mientras Gx Keybinds esté abierto, sus esperas y macros son más precisas.
- Plan de energía de alto rendimiento: evita que la CPU baje de frecuencia entre pulsaciones.
La latencia real de un juego depende sobre todo del monitor, el USB, los FPS y sus ajustes.
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable

HIGH_PERF_GUID = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
KB_DELAY_FASTEST, KB_SPEED_FASTEST = 0, 31          # SPI: 0 = 250 ms, 31 = ~30 caracteres/s
KB_DELAY_DEFAULT, KB_SPEED_DEFAULT = 1, 31          # valores por defecto de Windows (500 ms)
MOUSE_DEFAULT = (6, 10, 1)


class TweakError(RuntimeError):
    pass


class WinApi:
    """Acceso real a Windows (ctypes + powercfg)."""
    SPIF = 0x03   # UPDATEINIFILE | SENDCHANGE: persiste y avisa a las aplicaciones

    def __init__(self):
        import ctypes
        self.c = ctypes
        self.user32 = ctypes.windll.user32
        self.winmm = ctypes.windll.winmm
        self._timer = False

    def _get_uint(self, action: int) -> int:
        v = self.c.c_uint(0)
        if not self.user32.SystemParametersInfoW(action, 0, self.c.byref(v), 0):
            raise TweakError("No se pudo leer la configuración de Windows")
        return v.value

    def get_keyboard(self) -> tuple[int, int]:
        return self._get_uint(0x0016), self._get_uint(0x000A)      # delay, speed

    def set_keyboard(self, delay: int, speed: int) -> None:
        ok = self.user32.SystemParametersInfoW(0x0017, delay, None, self.SPIF)
        ok = ok and self.user32.SystemParametersInfoW(0x000B, speed, None, self.SPIF)
        if not ok:
            raise TweakError("Windows rechazó el cambio de repetición de teclas")

    def get_mouse(self) -> tuple[int, int, int]:
        arr = (self.c.c_int * 3)()
        if not self.user32.SystemParametersInfoW(0x0003, 0, arr, 0):
            raise TweakError("No se pudo leer la configuración del ratón")
        return tuple(arr)  # type: ignore[return-value]

    def set_mouse(self, t1: int, t2: int, acc: int) -> None:
        arr = (self.c.c_int * 3)(t1, t2, acc)
        if not self.user32.SystemParametersInfoW(0x0004, 0, arr, self.SPIF):
            raise TweakError("Windows rechazó el cambio del ratón")

    def timer_begin(self) -> None:
        if not self._timer:
            self.winmm.timeBeginPeriod(1)
            self._timer = True

    def timer_end(self) -> None:
        if self._timer:
            self.winmm.timeEndPeriod(1)
            self._timer = False

    @property
    def timer_active(self) -> bool:
        return self._timer

    def get_power_scheme(self) -> str:
        out = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True, timeout=10).stdout
        m = re.search(r"([0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})", out)
        if not m:
            raise TweakError("No se pudo leer el plan de energía")
        return m.group(1).lower()

    def set_power_scheme(self, guid: str) -> None:
        r = subprocess.run(["powercfg", "/setactive", guid], capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            raise TweakError("No se pudo cambiar el plan de energía (¿no existe «Alto rendimiento» en este equipo?)")


@dataclass
class Tweak:
    id: str
    label: str
    description: str
    is_on: Callable[[], bool]
    enable: Callable[[], None]
    disable: Callable[[], None]


class TweakManager:
    """Activa/desactiva ajustes guardando los valores originales en `store` para poder restaurarlos."""

    def __init__(self, api, store: dict, save: Callable[[], None] = lambda: None):
        self.api, self.store, self._save = api, store, save
        self.tweaks: list[Tweak] = [
            Tweak("keys", "Repetición de teclas al máximo",
                  "Retardo mínimo y velocidad máxima al mantener una tecla (no afecta pulsaciones simples).",
                  self._keys_on, self._keys_enable, self._keys_disable),
            Tweak("mouse", "Ratón sin aceleración",
                  "Desactiva «Mejorar la precisión del puntero»: movimiento 1:1 con la mano.",
                  self._mouse_on, self._mouse_enable, self._mouse_disable),
            Tweak("timer", "Temporizador de 1 ms",
                  "Más precisión en macros y esperas mientras Gx Keybinds esté abierto.",
                  lambda: self.api.timer_active, self.api.timer_begin, self.api.timer_end),
            Tweak("power", "Plan de energía: alto rendimiento",
                  "Evita que la CPU baje de frecuencia entre pulsaciones. Al apagarlo vuelve el plan anterior.",
                  self._power_on, self._power_enable, self._power_disable),
        ]

    def get(self, tid: str) -> Tweak:
        return next(t for t in self.tweaks if t.id == tid)

    def set(self, tid: str, on: bool) -> bool:
        """Activa/desactiva y devuelve el estado real resultante."""
        t = self.get(tid)
        (t.enable if on else t.disable)()
        return t.is_on()

    def restore_all(self) -> None:
        for t in self.tweaks:
            if t.is_on():
                t.disable()

    # --- respaldo de valores originales ---
    def _backup(self) -> dict:
        return self.store.setdefault("tweak_backup", {})

    def _remember(self, key: str, value) -> None:
        self._backup()[key] = list(value) if isinstance(value, tuple) else value
        self._save()

    # --- teclado ---
    def _keys_on(self) -> bool:
        return tuple(self.api.get_keyboard()) == (KB_DELAY_FASTEST, KB_SPEED_FASTEST)

    def _keys_enable(self) -> None:
        if not self._keys_on():
            self._remember("keys", self.api.get_keyboard())
        self.api.set_keyboard(KB_DELAY_FASTEST, KB_SPEED_FASTEST)

    def _keys_disable(self) -> None:
        d, s = self._backup().get("keys", (KB_DELAY_DEFAULT, KB_SPEED_DEFAULT))
        if (d, s) == (KB_DELAY_FASTEST, KB_SPEED_FASTEST):   # el original ya era el máximo
            d, s = KB_DELAY_DEFAULT, KB_SPEED_DEFAULT
        self.api.set_keyboard(d, s)

    # --- ratón ---
    def _mouse_on(self) -> bool:
        return self.api.get_mouse()[2] == 0

    def _mouse_enable(self) -> None:
        t1, t2, acc = self.api.get_mouse()
        if acc != 0:
            self._remember("mouse", (t1, t2, acc))
        self.api.set_mouse(t1, t2, 0)

    def _mouse_disable(self) -> None:
        t1, t2, acc = self._backup().get("mouse", MOUSE_DEFAULT)
        self.api.set_mouse(t1, t2, acc or 1)

    # --- energía ---
    def _power_on(self) -> bool:
        return self.api.get_power_scheme() == HIGH_PERF_GUID

    def _power_enable(self) -> None:
        cur = self.api.get_power_scheme()
        if cur != HIGH_PERF_GUID:
            self._remember("power", cur)
        self.api.set_power_scheme(HIGH_PERF_GUID)

    def _power_disable(self) -> None:
        prev = self._backup().get("power")
        if not prev or prev == HIGH_PERF_GUID:
            raise TweakError("No sé qué plan de energía tenías antes; cámbialo en Configuración de Windows.")
        self.api.set_power_scheme(prev)


def make_manager(store: dict, save: Callable[[], None]) -> TweakManager | None:
    """TweakManager real en Windows; None en otros sistemas."""
    if sys.platform != "win32":
        return None
    return TweakManager(WinApi(), store, save)
