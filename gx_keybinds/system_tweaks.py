"""Ajustes de Windows para mejorar la respuesta del teclado/ratón. Todos son reversibles.

Qué hace cada uno (y qué NO hace):
- Repetición rápida de teclas: retardo mínimo (250 ms) y velocidad máxima (~30/s) al MANTENER una tecla.
  No cambia la latencia de una pulsación simple.
- Ratón sin aceleración: desactiva «Mejorar la precisión del puntero» (movimiento 1:1).
- Temporizador del sistema 0.5 ms: la resolución mínima que permite Windows (mientras la app esté abierta).
- Macros a 0.01 ms: las esperas de las macros se hacen con espera activa (precisión de microsegundos,
  usa más CPU). Es la precisión con la que Gx Keybinds ENVÍA las teclas; lo que el juego lea depende de
  cuántas veces por segundo consulta el teclado (un teclado USB a 1000 Hz informa cada 1 ms como mínimo).
La latencia real de un juego depende sobre todo del monitor, el USB, los FPS y sus ajustes.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable

SPIN_PRECISE_S = 0.05      # espera activa en los últimos 50 ms de cada espera
KB_DELAY_FASTEST, KB_SPEED_FASTEST = 0, 31          # SPI: 0 = 250 ms, 31 = ~30 caracteres/s
KB_DELAY_DEFAULT, KB_SPEED_DEFAULT = 1, 31          # valores por defecto de Windows (500 ms)
MOUSE_DEFAULT = (6, 10, 1)


class TweakError(RuntimeError):
    pass


class WinApi:
    """Acceso real a Windows (ctypes)."""
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
        """Pide al sistema la resolución mínima del temporizador (0.5 ms; si no, 1 ms)."""
        if self._timer:
            return
        try:
            cur = self.c.c_ulong(0)
            self.c.windll.ntdll.NtSetTimerResolution(5000, True, self.c.byref(cur))   # unidades de 100 ns
            self._nt = True
        except (OSError, AttributeError):
            self.winmm.timeBeginPeriod(1)
            self._nt = False
        self._timer = True

    def timer_end(self) -> None:
        if not self._timer:
            return
        if getattr(self, "_nt", False):
            cur = self.c.c_ulong(0)
            self.c.windll.ntdll.NtSetTimerResolution(5000, False, self.c.byref(cur))
        else:
            self.winmm.timeEndPeriod(1)
        self._timer = False

    @property
    def timer_active(self) -> bool:
        return self._timer


@dataclass
class Tweak:
    id: str
    group: str          # sección de la GUI
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
            Tweak("keys", "Teclado", "Repetición de teclas al máximo",
                  "Retardo mínimo (250 ms) y velocidad máxima (~30/s) al MANTENER una tecla.",
                  self._keys_on, self._keys_enable, self._keys_disable),
            Tweak("timer", "Teclado", "Temporizador del sistema a 0.5 ms",
                  "Resolución mínima de Windows mientras Gx Keybinds esté abierto.",
                  lambda: self.api.timer_active, self.api.timer_begin, self.api.timer_end),
            Tweak("precise", "Teclado", "Macros a 0.01 ms (espera activa)",
                  "Esperas de macros con precisión de microsegundos. Usa más CPU mientras corre una macro.",
                  self._precise_on, self._precise_enable, self._precise_disable),
            Tweak("mouse", "Opcional", "Ratón sin aceleración",
                  "Desactiva «Mejorar la precisión del puntero»: movimiento 1:1 con la mano.",
                  self._mouse_on, self._mouse_enable, self._mouse_disable),
        ]
        if self.store.get("precise"):     # preferencia guardada
            self._precise_enable()

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

    # --- precisión de macros ---
    def _precise_on(self) -> bool:
        from . import engine
        return engine.SPIN_S >= SPIN_PRECISE_S

    def _precise_enable(self) -> None:
        from . import engine
        engine.SPIN_S = SPIN_PRECISE_S
        self.store["precise"] = True
        self._save()

    def _precise_disable(self) -> None:
        from . import engine
        engine.SPIN_S = 0.003
        self.store["precise"] = False
        self._save()


def make_manager(store: dict, save: Callable[[], None]) -> TweakManager | None:
    """TweakManager real en Windows; None en otros sistemas."""
    if sys.platform != "win32":
        return None
    return TweakManager(WinApi(), store, save)
