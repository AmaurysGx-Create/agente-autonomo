"""GUI mínima con tkinter: lista de macros, iniciar/detener, detener todo."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .backends import DryRunBackend
from .engine import Manager
from .model import MacroError, load_macros


def main() -> None:
    root = tk.Tk()
    root.title("MacroLab")
    state: dict = {"mgr": None, "macros": []}
    dry = tk.BooleanVar(value=True)

    tree = ttk.Treeview(root, columns=("trigger", "mode", "loop", "steps"), show="headings", height=10)
    for c, w in (("trigger", 90), ("mode", 70), ("loop", 60), ("steps", 60)):
        tree.heading(c, text=c)
        tree.column(c, width=w)
    tree.pack(fill="both", expand=True, padx=8, pady=8)

    def make_backend():
        if dry.get():
            return DryRunBackend(echo=True)
        from .backends import PynputBackend
        return PynputBackend()

    def open_file():
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            state["macros"] = load_macros(path)
        except (MacroError, OSError, ValueError) as e:
            messagebox.showerror("Error", str(e))
            return
        state["mgr"] = Manager(state["macros"], make_backend())
        tree.delete(*tree.get_children())
        for m in state["macros"]:
            tree.insert("", "end", iid=m.name, text=m.name,
                        values=(m.trigger or "-", m.mode, m.loop, len(m.steps)))

    def toggle():
        sel = tree.selection()
        if sel and state["mgr"]:
            state["mgr"].press(sel[0])

    def stop_all():
        if state["mgr"]:
            state["mgr"].stop_all()

    bar = ttk.Frame(root)
    bar.pack(fill="x", padx=8, pady=(0, 8))
    ttk.Button(bar, text="Abrir…", command=open_file).pack(side="left")
    ttk.Button(bar, text="Iniciar/Parar", command=toggle).pack(side="left", padx=4)
    ttk.Button(bar, text="PARAR TODO", command=stop_all).pack(side="left")
    ttk.Checkbutton(bar, text="Simulación (dry-run)", variable=dry).pack(side="right")
    root.protocol("WM_DELETE_WINDOW", lambda: (stop_all(), root.destroy()))
    root.mainloop()
