"""Icono en la bandeja del sistema (junto al reloj) con menú: mostrar, atajos, editor, ajustes, salir.

Los manejadores se ejecutan en el hilo de la bandeja: quien llame debe pasarlos al hilo de la
interfaz (ver `ui_queue` en gui.py). Si pystray no está disponible, `make_tray` devuelve None.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

ICON_PATH = Path(__file__).with_name("icon.png")


class Tray:
    def __init__(self, icon, handlers: dict[str, Callable[[], None]]):
        self._icon = icon
        self.handlers = handlers

    def start(self) -> None:
        # Hilo daemon propio (no run_detached): si el icono no llega a acoplarse, no impide cerrar el proceso.
        threading.Thread(target=self._icon.run, daemon=True, name="tray").start()

    def stop(self) -> None:
        """Quita el icono sin bloquear la interfaz (pystray puede tardar en cerrar su hilo)."""
        def _stop():
            try:
                self._icon.stop()
            except Exception:
                pass
        threading.Thread(target=_stop, daemon=True, name="tray-stop").start()

    def refresh(self) -> None:
        """Vuelve a evaluar los textos del menú (p. ej. «Iniciar» ↔ «Detener» atajos)."""
        try:
            self._icon.update_menu()
        except Exception:
            pass

    def notify(self, message: str, title: str = "Gx Keybinds") -> None:
        try:
            self._icon.notify(message, title)
        except Exception:
            pass   # no todos los entornos soportan notificaciones

    def invoke(self, name: str) -> None:
        """Ejecuta una entrada del menú (para pruebas)."""
        self.handlers[name]()


def make_tray(handlers: dict[str, Callable[[], None]], is_running: Callable[[], bool],
              title: str = "Gx Keybinds") -> Tray | None:
    """handlers: show, toggle, editor, settings, exit. is_running: ¿están activos los atajos?"""
    try:
        import pystray
        from PIL import Image
        image = Image.open(ICON_PATH)
    except Exception:
        return None

    def act(name: str):
        return lambda icon, item: handlers[name]()

    menu = pystray.Menu(
        pystray.MenuItem("Mostrar Gx Keybinds", act("show"), default=True),   # clic izquierdo
        pystray.MenuItem(lambda item: "Detener atajos" if is_running() else "Iniciar atajos", act("toggle")),
        pystray.MenuItem("Editor de macros", act("editor")),
        pystray.MenuItem("Ajustes", act("settings")),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Salir", act("exit")),
    )
    try:
        icon = pystray.Icon("GxKeybinds", image, title, menu)
    except Exception:
        return None
    return Tray(icon, handlers)
