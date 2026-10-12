"""Teclado en pantalla (tkinter Canvas): clic en una tecla => callback con el nombre de la tecla."""
from __future__ import annotations

import tkinter as tk

from .keyboard_layout import key_rects
from .themes import Palette, current_palette

UNIT, GAP = 34, 3


class OnScreenKeyboard(tk.Canvas):
    def __init__(self, parent, on_key, **kw):
        self._rects = key_rects(UNIT, GAP)
        w = max(x + rw for _, _, x, _, rw, _ in self._rects) + 2
        h = max(y + rh for _, _, _, y, _, rh in self._rects) + 2
        super().__init__(parent, width=w, height=h, highlightthickness=0, **kw)
        self.on_key = on_key
        self.used: set[str] = set()
        self.selected: set[str] = set()
        self._hover: str | None = None
        self._ids: dict[str, tuple[int, int]] = {}   # tecla -> (rect, texto)
        self.bind("<Button-1>", self._click)
        self.bind("<Motion>", self._motion)
        self.bind("<Leave>", lambda e: self._set_hover(None))
        self.redraw()

    def _key_at(self, x: int, y: int) -> str | None:
        for _, key, rx, ry, rw, rh in self._rects:
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return key
        return None

    def _click(self, e) -> None:
        k = self._key_at(e.x, e.y)
        if k:
            self.on_key(k)

    def _motion(self, e) -> None:
        self._set_hover(self._key_at(e.x, e.y))

    def _set_hover(self, key: str | None) -> None:
        if key != self._hover:
            old, self._hover = self._hover, key
            for k in (old, key):
                if k:
                    self._paint(k)

    def set_highlight(self, used: set[str], selected: set[str]) -> None:
        self.used, self.selected = used, selected
        for k in self._ids:
            self._paint(k)

    def _colors(self, key: str, p: Palette) -> tuple[str, str]:
        if key in self.selected:
            return p.accent, p.accent_fg
        if key == self._hover:
            return p.button_active, p.fg
        if key in self.used:
            return p.loop_bg, p.fg
        return p.surface, p.fg

    def _paint(self, key: str) -> None:
        p = current_palette()
        fill, fg = self._colors(key, p)
        rid, tid = self._ids[key]
        self.itemconfigure(rid, fill=fill, outline=p.border)
        self.itemconfigure(tid, fill=fg)

    def redraw(self) -> None:
        """(Re)dibuja todo; llamar también tras cambiar de tema."""
        p = current_palette()
        self.configure(bg=p.bg)
        self.delete("all")
        self._ids.clear()
        for label, key, x, y, w, h in self._rects:
            rid = self.create_rectangle(x + 1, y + 1, x + w, y + h, fill=p.surface, outline=p.border)
            size = 7 if len(label) > 4 else 9
            tid = self.create_text(x + w / 2 + 0.5, y + h / 2 + 0.5, text=label, fill=p.fg,
                                   font=("TkDefaultFont", size))
            self._ids[key] = (rid, tid)
        for k in self._ids:
            self._paint(k)
