"""GUI mínima con tkinter: lista de macros, iniciar/detener, detener todo."""
from __future__ import annotations

import queue
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .backends import DryRunBackend
from .engine import Manager
from .settings import load_settings, save_settings
from .themes import apply_theme, current_palette, system_prefers_dark
from .model import Macro, MacroError, load_macros, save_macros


def _loop_text(loop) -> str:
    return "∞" if loop is True else ("1" if loop is False else str(loop))


def main() -> None:
    root = tk.Tk()
    root.title("Gx Keybinds")
    root.geometry("960x560")
    root.minsize(760, 380)
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
    root.columnconfigure(0, weight=1)
    root.rowconfigure(1, weight=1)       # solo la zona central (lista + ajustes) cede espacio
    pbar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
    ttk.Label(pbar, text="Perfil").pack(side="left")
    profile_cb = ttk.Combobox(pbar, textvariable=profile_var, state="disabled", width=30)
    profile_cb.pack(side="left", padx=6)
    profile_cb.bind("<<ComboboxSelected>>", lambda e: use_profile(profile_var.get()))
    ttk.Checkbutton(pbar, text="Automático (ventana activa)", variable=auto_var).pack(side="left")

    body = ttk.Frame(root)
    body.grid(row=1, column=0, sticky="nsew")
    tree = ttk.Treeview(body, columns=("name", "trigger", "mode", "loop", "steps"),
                        show="headings", height=10)
    for c, title, w in (("name", "Macro", 260), ("trigger", "Tecla", 80), ("mode", "Modo", 80),
                        ("loop", "Repetir", 80), ("steps", "Pasos", 60)):
        tree.heading(c, text=title)
        tree.column(c, width=w, anchor="w")
    tree.pack(side="left", fill="both", expand=True, padx=8, pady=8)

    # --- Columna «Respuesta e input lag»: interruptores de ajustes de Windows (reversibles) ---
    from .system_tweaks import TweakError, make_manager
    tweaks = make_manager(settings, lambda: save_settings(settings))
    side_wrap = ttk.Frame(body)
    side_wrap.pack(side="right", fill="y", padx=(0, 8), pady=8, before=tree)   # primero: es lo que no debe recortarse
    side_canvas = tk.Canvas(side_wrap, width=272, highlightthickness=0, bd=0)
    side_scroll = ttk.Scrollbar(side_wrap, orient="vertical", command=side_canvas.yview)
    side_canvas.configure(yscrollcommand=side_scroll.set)
    side_canvas.pack(side="left", fill="y")
    side_scroll.pack(side="left", fill="y")
    side = ttk.LabelFrame(side_canvas, text="Respuesta e input lag", padding=8)
    side_canvas.create_window((0, 0), window=side, anchor="nw", width=268)
    side.bind("<Configure>", lambda e: side_canvas.configure(scrollregion=side_canvas.bbox("all")))
    side_canvas.bind("<Enter>", lambda e: side_canvas.bind_all(
        "<MouseWheel>", lambda ev: side_canvas.yview_scroll(-1 * (ev.delta // 120), "units")))
    side_canvas.bind("<Leave>", lambda e: side_canvas.unbind_all("<MouseWheel>"))
    side_canvas.configure(bg=current_palette().bg)
    tweak_vars: dict = {}
    if tweaks is None:
        ttk.Label(side, text="Disponible solo en Windows.", wraplength=215).pack()
    else:
        def on_tweak(tid):
            if not tweak_vars[tid].get() and not tweaks.can_restore(tid):
                if not messagebox.askyesno(
                        "Volver a los valores de Windows",
                        "Este ajuste ya estaba activo antes de abrir Gx Keybinds, así que no tengo "
                        "guardado tu valor original.\n\nSi lo apagas, vuelve al valor por defecto de "
                        "Windows. ¿Continuar?"):
                    tweak_vars[tid].set(True)
                    return
            try:
                tweak_vars[tid].set(tweaks.set(tid, tweak_vars[tid].get()))
            except (TweakError, OSError) as e:
                tweak_vars[tid].set(tweaks.get(tid).is_on())
                messagebox.showerror("Ajuste de Windows", str(e))
        last_group = None
        for t in tweaks.tweaks:
            if t.group != last_group:
                last_group = t.group
                ttk.Label(side, text=t.group.upper() if t.group != "Opcional" else "OPCIONAL",
                          font=("TkDefaultFont", 8, "bold")).pack(anchor="w", pady=(10, 0))
            try:
                on = t.is_on()
            except (TweakError, OSError):
                on = False
            tweak_vars[t.id] = tk.BooleanVar(value=on)
            ttk.Checkbutton(side, text=f"{t.label}", variable=tweak_vars[t.id],
                            command=lambda i=t.id: on_tweak(i)).pack(anchor="w", pady=(6, 0))
            ttk.Label(side, text=t.description, wraplength=215).pack(anchor="w", padx=(20, 0))

        def restore_tweaks():
            try:
                tweaks.restore_all()
            except (TweakError, OSError) as e:
                messagebox.showerror("Ajuste de Windows", str(e))
            for t in tweaks.tweaks:
                tweak_vars[t.id].set(t.is_on())
        ttk.Button(side, text="Apagar los que activé yo", command=restore_tweaks).pack(
            fill="x", pady=(0, 4), before=side.winfo_children()[0])

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

    # tkinter no es seguro entre hilos (root.after desde otro hilo puede no ejecutarse nunca):
    # los hilos de pynput dejan aquí sus avisos y el hilo de Tk los atiende cada 50 ms.
    ui_queue: queue.SimpleQueue = queue.SimpleQueue()

    def drain_ui_queue():
        try:
            while True:
                ui_queue.get_nowait()()
        except queue.Empty:
            pass
        root.after(50, drain_ui_queue)

    tray_ref: dict = {"t": None}

    def refresh_tray():
        if tray_ref["t"]:
            tray_ref["t"].refresh()

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
                                on_panic=lambda: ui_queue.put(panic_ui))
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
        refresh_tray()

    def on_hotkeys_toggle():
        if hotkeys_var.get():
            if hotkeys_start():
                status.set("Atajos globales activos. F12 = pánico (detiene todo).")
            else:
                hotkeys_var.set(False)
        else:
            hotkeys_stop()
            status.set("Atajos globales desactivados.")
        refresh_tray()

    def refresh():
        if state["mgr"]:
            state["mgr"].stop_all()   # no dejar macros huérfanas al reconstruir
        tree.delete(*tree.get_children())
        for m in state["macros"]:
            tree.insert("", "end", iid=m.name, text=m.name,
                        values=(m.name, m.trigger or "-", m.mode, _loop_text(m.loop), len(m.steps)))
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
            # F12 también detiene; el callback llega desde otro hilo -> cola ui_queue
            lr = LiveRecorder(stop_key="f12", record_moves=moves.get(),
                              on_stop=lambda: ui_queue.put(finish_recording))
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
    bar.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 4))
    bar2 = ttk.Frame(root)      # segunda fila: opciones (si no, no caben en ventanas estrechas)
    bar2.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 8))
    ttk.Button(bar, text="Abrir…", command=open_file).pack(side="left")
    ttk.Button(bar, text="Iniciar/Parar", command=toggle).pack(side="left", padx=4)
    ttk.Button(bar, text="PARAR TODO", command=stop_all).pack(side="left")
    rec_btn = ttk.Button(bar, text="● Grabar", command=toggle_record)
    rec_btn.pack(side="left", padx=4)
    ttk.Button(bar, text="Guardar…", command=save_file).pack(side="left")
    ttk.Button(bar, text="Nueva", command=new_macro).pack(side="left", padx=(8, 0))
    ttk.Button(bar, text="Editar pasos…", command=edit_macro).pack(side="left", padx=4)
    moves = tk.BooleanVar(value=False)
    ttk.Checkbutton(bar2, text="Grabar movimiento", variable=moves).pack(side="left", padx=(0, 8))
    ttk.Checkbutton(bar2, text="Simulación (dry-run)", variable=dry).pack(side="left", padx=8)
    ttk.Checkbutton(bar2, text="Atajos globales", variable=hotkeys_var,
                    command=on_hotkeys_toggle).pack(side="left", padx=8)

    def toggle_dark():
        dark_var.set(not dark_var.get())
        apply_theme(root, dark_var.get())
        side_canvas.configure(bg=current_palette().bg)
        theme_btn.config(text=theme_label())
        settings["dark"] = dark_var.get()
        save_settings(settings)

    def theme_label():
        return "☀ Modo claro" if dark_var.get() else "🌙 Modo oscuro"

    theme_btn = ttk.Button(bar2, text=theme_label(), command=toggle_dark)
    theme_btn.pack(side="right")
    ttk.Label(root, textvariable=status).grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 6))
    # --- Bandeja del sistema: icono junto al reloj con menú (Mostrar / Atajos / Editor / Ajustes / Salir) ---
    from .tray import make_tray

    def show_window():
        root.deiconify()
        root.lift()
        root.focus_force()

    def tray_toggle():
        hotkeys_var.set(not hotkeys_var.get())
        on_hotkeys_toggle()

    def tray_editor():
        show_window()
        if not tree.selection() and tree.get_children():
            tree.selection_set(tree.get_children()[0])
        edit_macro()

    def open_settings():
        show_window()
        win = tk.Toplevel(root)
        win.title("Ajustes")
        win.transient(root)
        win.resizable(False, False)
        f = ttk.Frame(win, padding=14)
        f.pack()
        v_close = tk.BooleanVar(value=settings.get("tray_on_close", True))
        v_start = tk.BooleanVar(value=settings.get("start_in_tray", False))
        v_dark = tk.BooleanVar(value=dark_var.get())

        def save():
            settings["tray_on_close"] = v_close.get()
            settings["start_in_tray"] = v_start.get()
            save_settings(settings)

        def on_dark():
            if v_dark.get() != dark_var.get():
                toggle_dark()

        ttk.Checkbutton(f, text="Al cerrar la ventana, seguir en segundo plano (bandeja)",
                        variable=v_close, command=save).pack(anchor="w", pady=2)
        ttk.Checkbutton(f, text="Iniciar minimizado en la bandeja", variable=v_start,
                        command=save).pack(anchor="w", pady=2)
        ttk.Checkbutton(f, text="Modo oscuro", variable=v_dark, command=on_dark).pack(anchor="w", pady=2)
        ttk.Label(f, text="«Salir» en el menú de la bandeja cierra el programa por completo.",
                  wraplength=360).pack(anchor="w", pady=(10, 6))
        ttk.Button(f, text="Cerrar", command=win.destroy).pack(anchor="e")

    def quit_all():
        if tray_ref["t"]:
            tray_ref["t"].stop()
        if tweaks is not None and tweaks.api.timer_active:
            tweaks.api.timer_end()    # el temporizador de 0.5 ms solo vale mientras la app está abierta
        hotkeys_stop()
        stop_all()
        if rec_state["lr"] is not None:
            rec_state["lr"].stop()
        root.destroy()

    def on_close():
        if tray_ref["t"] and settings.get("tray_on_close", True):
            root.withdraw()           # sigue funcionando en segundo plano
            if not settings.get("tray_hint_shown"):
                settings["tray_hint_shown"] = True
                save_settings(settings)
                tray_ref["t"].notify("Sigue activo en la bandeja. Clic derecho → Salir para cerrarlo del todo.")
        else:
            quit_all()

    def to_ui(fn):
        return lambda: ui_queue.put(fn)   # el menú de la bandeja corre en otro hilo

    tray_ref["t"] = make_tray(
        {"show": to_ui(show_window), "toggle": to_ui(tray_toggle), "editor": to_ui(tray_editor),
         "settings": to_ui(open_settings), "exit": to_ui(quit_all)},
        is_running=lambda: bool(hk["hl"]))
    if tray_ref["t"]:
        tray_ref["t"].start()
        if settings.get("start_in_tray"):
            root.withdraw()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.after(500, auto_tick)
    root.after(50, drain_ui_queue)
    root.mainloop()
