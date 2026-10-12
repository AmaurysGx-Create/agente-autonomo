"""Temas claro/oscuro para la GUI (ttk + widgets tk clásicos)."""
from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    bg: str
    surface: str      # campos de texto, listas
    fg: str
    muted: str
    accent: str       # selección
    accent_fg: str
    border: str
    button: str
    button_active: str
    loop_bg: str      # fila marcada como inicio de bucle en el editor


LIGHT = Palette("#f0f0f0", "#ffffff", "#1a1a1a", "#555555", "#2563eb", "#ffffff",
                "#c4c4c4", "#e1e1e1", "#d0d0d0", "#dbeafe")
DARK = Palette("#1b2230", "#232c3d", "#e6e9ef", "#9aa4b5", "#3b82f6", "#ffffff",
               "#3a465c", "#2d3850", "#3a4868", "#1e3a5f")

_current = LIGHT


def current_palette() -> Palette:
    return _current


def system_prefers_dark() -> bool:
    """Mejor esfuerzo: tema de aplicaciones de Windows. En otros sistemas, False."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
    except OSError:
        return False


def apply_theme(root, dark: bool) -> Palette:
    """Aplica el tema a toda la aplicación (incluidas ventanas Toplevel futuras)."""
    from tkinter import ttk
    global _current
    p = _current = DARK if dark else LIGHT
    style = ttk.Style(root)
    style.theme_use("clam")   # el único tema de ttk que respeta todos los colores
    root.tk_setPalette(background=p.bg, foreground=p.fg, activeBackground=p.button_active,
                       activeForeground=p.fg, highlightBackground=p.bg, selectBackground=p.accent,
                       selectForeground=p.accent_fg, troughColor=p.surface)
    root.configure(bg=p.bg)
    style.configure(".", background=p.bg, foreground=p.fg, fieldbackground=p.surface,
                    bordercolor=p.border, lightcolor=p.bg, darkcolor=p.bg, troughcolor=p.surface,
                    focuscolor=p.accent)
    style.configure("TLabel", background=p.bg, foreground=p.fg)
    style.configure("TFrame", background=p.bg)
    style.configure("TButton", background=p.button, foreground=p.fg, bordercolor=p.border, padding=5)
    style.map("TButton", background=[("active", p.button_active), ("pressed", p.button_active)])
    style.configure("TCheckbutton", background=p.bg, foreground=p.fg)
    style.map("TCheckbutton", background=[("active", p.bg)], foreground=[("disabled", p.muted)])
    style.configure("TLabelframe", background=p.bg, bordercolor=p.border)
    style.configure("TLabelframe.Label", background=p.bg, foreground=p.fg)
    style.configure("TRadiobutton", background=p.bg, foreground=p.fg)
    style.map("TRadiobutton", background=[("active", p.bg)], foreground=[("disabled", p.muted)])
    style.configure("TEntry", fieldbackground=p.surface, foreground=p.fg, insertcolor=p.fg)
    style.configure("TCombobox", fieldbackground=p.surface, background=p.button, foreground=p.fg,
                    arrowcolor=p.fg, selectbackground=p.surface, selectforeground=p.fg)
    style.map("TCombobox", fieldbackground=[("readonly", p.surface), ("disabled", p.bg)],
              foreground=[("disabled", p.muted)], selectbackground=[("readonly", p.surface)],
              selectforeground=[("readonly", p.fg)])
    root.option_add("*TCombobox*Listbox.background", p.surface)
    root.option_add("*TCombobox*Listbox.foreground", p.fg)
    root.option_add("*TCombobox*Listbox.selectBackground", p.accent)
    root.option_add("*TCombobox*Listbox.selectForeground", p.accent_fg)
    style.configure("Treeview", background=p.surface, fieldbackground=p.surface, foreground=p.fg,
                    bordercolor=p.border)
    style.map("Treeview", background=[("selected", p.accent)], foreground=[("selected", p.accent_fg)])
    style.configure("Treeview.Heading", background=p.button, foreground=p.fg, bordercolor=p.border)
    style.map("Treeview.Heading", background=[("active", p.button_active)])
    style.configure("Vertical.TScrollbar", background=p.button, troughcolor=p.bg, arrowcolor=p.fg,
                    bordercolor=p.border)
    return p
