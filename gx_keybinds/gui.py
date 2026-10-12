"""GUI mínima con tkinter: lista de macros, iniciar/detener, detener todo."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .backends import DryRunBackend
from .engine import Manager
from .settings import load_settings, save_settings
from .themes import apply_theme, system_prefers_dark
from .model import Macro, MacroError, load_macros, save_macros


def main() -> None:
    root = tk.Tk()
    root.title("Gx Keybinds")
    try:  # icono de la ventana/barra de tareas (también dentro del .exe de PyInstaller)
        from pathlib import Path
        root._icon = tk.PhotoImage(file=str(Path(__file__).with_name("icon.png")))
        root.iconphoto(True, root._icon)
    except Exception:
        pass
    state: dict = {"mgr": None, "macros": []}
    settings = load_settings()
    dark_var = tk.BooleanVar(value=settings.get("dark", system_prefers_dark()))
    apply_theme(root, dark_var.get())
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

    class _CurrentManager:
        """Delegado: los atajos globales siempre usan el Manager actual (cambia al editar/perfil)."""
        def _m(self): return state["mgr"]
        def lookup(self, t): m = self._m(); return m.lookup(t) if m else None
        def press(self, n):
            m = self._m()
            if m and n in m.runners: m.press(n)
        def release(self, n):
            m = self._m()
            if m and n in m.runners: m.release(n)
        def stop_all(self):
            m = self._m()
            if m: m.stop_all()

    hotkeys_var = tk.BooleanVar(value=False)
    hk: dict = {"hl": None}

    def hotkeys_stop():
        if hk["hl"]:
            hk["hl"].stop()
            hk["hl"] = None

    def hotkeys_start() -> bool:
        if hk["hl"]:
            return True
        dups = state["mgr"].duplicate_triggers() if state["mgr"] else []
        if dups:
            messagebox.showwarning("Teclas repetidas",
                                   "Estas teclas están asignadas a varias macros: " + ", ".join(dups))
        try:
            from .hotkeys import HotkeyListener
            hl = HotkeyListener(_CurrentManager(), panic="f12",
                                on_panic=lambda: root.after(0, panic_ui))
            hl.start()
        except Exception as e:  # sin entorno gráfico / sin pynput
            messagebox.showerror("Atajos globales", str(e))
            return False
        hk["hl"] = hl
        return True

    def panic_ui():
        hotkeys_var.set(False)
        status.set("PÁNICO (F12): macros detenidas y atajos globales desactivados.")
        hotkeys_stop()

    def on_hotkeys_toggle():
        if hotkeys_var.get():
            if hotkeys_start():
                status.set("Atajos globales activos. F12 = pánico (detiene todo).")
            else:
                hotkeys_var.set(False)
        else:
            hotkeys_stop()
            status.set("Atajos globales desactivados.")

    def refresh():
        if state["mgr"]:
            state["mgr"].stop_all()   # no dejar macros huérfanas al reconstruir
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
        if rec_state.pop("resume_hotkeys", False):
            hotkeys_var.set(hotkeys_start())
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
        if hk["hl"]:   # F12 y las teclas grabadas no deben disparar macros durante la grabación
            hotkeys_stop()
            rec_state["resume_hotkeys"] = True
        try:
            from .recorder import LiveRecorder
            # F12 también detiene; el callback llega desde otro hilo -> root.after
            lr = LiveRecorder(stop_key="f12", record_moves=moves.get(),
                              on_stop=lambda: root.after(0, finish_recording))
            lr.start()
        except Exception as e:  # sin entorno gráfico / sin pynput
            messagebox.showerror("No se puede grabar", str(e))
            if rec_state.pop("resume_hotkeys", False):
                hotkeys_var.set(hotkeys_start())
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
    ttk.Checkbutton(bar, text="Atajos globales", variable=hotkeys_var,
                    command=on_hotkeys_toggle).pack(side="right", padx=8)

    def toggle_dark():
        dark_var.set(not dark_var.get())
        apply_theme(root, dark_var.get())
        theme_btn.config(text=theme_label())
        settings["dark"] = dark_var.get()
        save_settings(settings)

    def theme_label():
        return "☀ Modo claro" if dark_var.get() else "🌙 Modo oscuro"

    theme_btn = ttk.Button(bar, text=theme_label(), command=toggle_dark)
    theme_btn.pack(side="right", padx=8)
    ttk.Label(root, textvariable=status).pack(fill="x", padx=8, pady=(0, 6))
    def on_close():
        hotkeys_stop()
        stop_all()
        if rec_state["lr"] is not None:
            rec_state["lr"].stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.after(500, auto_tick)
    root.mainloop()
