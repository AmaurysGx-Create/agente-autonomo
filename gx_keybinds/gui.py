"""GUI mínima con tkinter: lista de macros, iniciar/detener, detener todo."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .backends import DryRunBackend
from .engine import Manager
from .model import Macro, MacroError, load_macros, save_macros


def main() -> None:
    root = tk.Tk()
    root.title("Gx Keybinds")
    state: dict = {"mgr": None, "macros": []}
    dry = tk.BooleanVar(value=True)

    profile_var = tk.StringVar()
    auto_var = tk.BooleanVar(value=False)
    pbar = ttk.Frame(root)
    pbar.pack(fill="x", padx=8, pady=(8, 0))
    ttk.Label(pbar, text="Perfil").pack(side="left")
    profile_cb = ttk.Combobox(pbar, textvariable=profile_var, state="disabled", width=30)
    profile_cb.pack(side="left", padx=6)
    profile_cb.bind("<<ComboboxSelected>>", lambda e: use_profile(profile_var.get()))
    ttk.Checkbutton(pbar, text="Automático (ventana activa)", variable=auto_var).pack(side="left")

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
        path = filedialog.askopenfilename(filetypes=[("Gx Keybinds / Keyran", "*.json *.amc"), ("Todos", "*.*")])
        if not path:
            return
        try:
            from .profiles import is_profile_file, load_profiles
            if is_profile_file(path):
                state["pset"] = load_profiles(path)
                names = [p.name for p in state["pset"].profiles]
                profile_cb.config(values=names, state="readonly")
                profile_var.set(names[0] if names else "")
                use_profile(profile_var.get())
                return
            state["pset"] = None
            profile_cb.config(values=[], state="disabled")
            profile_var.set("")
            state["macros"] = load_macros(path)
        except (MacroError, OSError, ValueError) as e:
            messagebox.showerror("Error", str(e))
            return
        refresh()

    def use_profile(name):
        """Muestra las macros de un perfil (la lista es la misma del perfil: editar la modifica)."""
        stop_all()
        if state.get("pset") and name:
            state["macros"] = state["pset"].get(name).macros
            refresh()

    def auto_tick():
        # Cambia de perfil según la ventana activa (no mientras se graba o edita).
        if auto_var.get() and state.get("pset") and rec_state["lr"] is None and not state.get("editing"):
            from .active_window import get_active_window
            p = state["pset"].select(get_active_window())
            if p and p.name != profile_var.get():
                profile_var.set(p.name)
                use_profile(p.name)
                status.set(f"Perfil automático: {p.name}")
        root.after(500, auto_tick)

    def toggle():
        sel = tree.selection()
        if sel and state["mgr"]:
            state["mgr"].press(sel[0])

    def stop_all():
        if state["mgr"]:
            state["mgr"].stop_all()

    rec_state: dict = {"lr": None}
    status = tk.StringVar(value="")
    rec_btn = None

    def refresh():
        tree.delete(*tree.get_children())
        for m in state["macros"]:
            tree.insert("", "end", iid=m.name, text=m.name,
                        values=(m.trigger or "-", m.mode, m.loop, len(m.steps)))
        state["mgr"] = Manager(state["macros"], make_backend())

    def finish_recording():
        """Se ejecuta en el hilo de Tk: cierra la grabación y añade la macro."""
        lr = rec_state["lr"]
        if lr is None:
            return
        lr.stop()
        rec_state["lr"] = None
        rec_btn.config(text="● Grabar")
        status.set("")
        if not lr.rec.events:
            messagebox.showinfo("Grabación", "No se grabó ningún evento.")
            return
        name = simpledialog.askstring("Nombre", "Nombre de la macro grabada:", parent=root)
        if not name:
            return
        if name in {m.name for m in state["macros"]}:
            name += " (2)"
        try:
            m = lr.to_macro(name, mode="once")
        except MacroError as e:
            messagebox.showerror("Error", str(e))
            return
        state["macros"].append(m)
        refresh()
        status.set(f"Grabada '{name}' ({len(m.steps)} pasos). Usa «Guardar…» para exportarla.")

    def toggle_record():
        if rec_state["lr"] is not None:
            finish_recording()
            return
        stop_all()
        try:
            from .recorder import LiveRecorder
            # F12 también detiene; el callback llega desde otro hilo -> root.after
            lr = LiveRecorder(stop_key="f12", record_moves=moves.get(),
                              on_stop=lambda: root.after(0, finish_recording))
            lr.start()
        except Exception as e:  # sin entorno gráfico / sin pynput
            messagebox.showerror("No se puede grabar", str(e))
            return
        rec_state["lr"] = lr
        rec_btn.config(text="■ Detener")
        status.set("Grabando… pulsa F12 o «Detener» para terminar.")

    def edit_macro():
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Editor", "Selecciona una macro de la lista.")
            return
        macro = next(m for m in state["macros"] if m.name == sel[0])
        stop_all()
        from .editor import MacroEditor
        state["editing"] = True
        try:
            ed = MacroEditor(root, macro)
        finally:
            state["editing"] = False
        if ed.saved:
            refresh()

    def new_macro():
        name, n = "nueva_macro", 1
        names = {m.name for m in state["macros"]}
        while name in names:
            n += 1
            name = f"nueva_macro_{n}"
        state["macros"].append(Macro(name=name, mode="once"))
        refresh()
        tree.selection_set(name)
        edit_macro()

    def save_file():
        if not state["macros"]:
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            if state.get("pset"):   # guarda todos los perfiles, no solo el visible
                from .profiles import save_profiles
                save_profiles(path, state["pset"])
            else:
                save_macros(path, state["macros"])
            status.set(f"Guardado en {path}")

    bar = ttk.Frame(root)
    bar.pack(fill="x", padx=8, pady=(0, 8))
    ttk.Button(bar, text="Abrir…", command=open_file).pack(side="left")
    ttk.Button(bar, text="Iniciar/Parar", command=toggle).pack(side="left", padx=4)
    ttk.Button(bar, text="PARAR TODO", command=stop_all).pack(side="left")
    rec_btn = ttk.Button(bar, text="● Grabar", command=toggle_record)
    rec_btn.pack(side="left", padx=4)
    ttk.Button(bar, text="Guardar…", command=save_file).pack(side="left")
    ttk.Button(bar, text="Nueva", command=new_macro).pack(side="left", padx=(8, 0))
    ttk.Button(bar, text="Editar pasos…", command=edit_macro).pack(side="left", padx=4)
    moves = tk.BooleanVar(value=False)
    ttk.Checkbutton(bar, text="Grabar movimiento", variable=moves).pack(side="left", padx=8)
    ttk.Checkbutton(bar, text="Simulación (dry-run)", variable=dry).pack(side="right")
    ttk.Label(root, textvariable=status).pack(fill="x", padx=8, pady=(0, 6))
    def on_close():
        stop_all()
        if rec_state["lr"] is not None:
            rec_state["lr"].stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.after(500, auto_tick)
    root.mainloop()
