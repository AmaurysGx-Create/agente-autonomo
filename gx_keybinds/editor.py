"""Editor visual de pasos (tkinter): ventana modal para editar una macro."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .editor_model import FIELDS, StepEditor, build_step, describe, duration_ms, step_values
from .model import Macro, MacroError, Step
from .keyboard_layout import keys_used, step_for_key
from .keyboard_widget import OnScreenKeyboard
from .themes import current_palette


class StepDialog(tk.Toplevel):
    """Formulario para crear/editar un paso; `result` queda en None si se cancela."""

    def __init__(self, parent, step: Step | None = None):
        super().__init__(parent)
        self.title("Editar paso" if step else "Nuevo paso")
        self.transient(parent)
        self.resizable(False, False)
        self.result: Step | None = None
        self._vars: dict[str, tk.StringVar] = {}
        self._type = tk.StringVar(value=step.type if step else "tap")
        self._initial = step_values(step) if step else {}

        top = ttk.Frame(self, padding=10)
        top.pack(fill="both")
        ttk.Label(top, text="Tipo").grid(row=0, column=0, sticky="w")
        cb = ttk.Combobox(top, textvariable=self._type, values=list(FIELDS), state="readonly", width=12)
        cb.grid(row=0, column=1, sticky="ew", pady=2)
        cb.bind("<<ComboboxSelected>>", lambda e: self._build_fields())
        self._form = ttk.Frame(top)
        self._form.grid(row=1, column=0, columnspan=2, sticky="ew")
        btns = ttk.Frame(top)
        btns.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky="e")
        ttk.Button(btns, text="Aceptar", command=self._ok).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side="left")
        self._build_fields()
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()
        self.wait_window()

    def _build_fields(self) -> None:
        for w in self._form.winfo_children():
            w.destroy()
        self._vars.clear()
        for r, (attr, label, _kind, default) in enumerate(FIELDS[self._type.get()]):
            ttk.Label(self._form, text=label).grid(row=r, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=self._initial.get(attr, str(default)))
            self._vars[attr] = var
            e = ttk.Entry(self._form, textvariable=var, width=28)
            e.grid(row=r, column=1, padx=(8, 0), pady=2)
            if r == 0:
                e.focus_set()

    def _ok(self) -> None:
        try:
            self.result = build_step(self._type.get(), {k: v.get() for k, v in self._vars.items()})
        except MacroError as e:
            messagebox.showerror("Paso inválido", str(e), parent=self)
            return
        self.destroy()


class MacroEditor(tk.Toplevel):
    """Edita nombre, disparador, modo, bucle y la lista de pasos de una macro."""

    def __init__(self, parent, macro: Macro):
        super().__init__(parent)
        self.title(f"Editor — {macro.name}")
        self.geometry("880x720")
        self.minsize(820, 680)
        self.transient(parent)
        self.macro = macro
        self.ed = StepEditor(macro)
        self.saved = False

        props = ttk.Frame(self, padding=(8, 8, 8, 0))
        props.pack(fill="x")
        self.v_name = tk.StringVar(value=macro.name)
        self.v_trigger = tk.StringVar(value=macro.trigger or "")
        self.v_mode = tk.StringVar(value=macro.mode)
        self.v_loop = tk.StringVar(value="inf" if macro.loop is True else
                                   ("1" if macro.loop is False else str(macro.loop)))
        for col, (label, var, w) in enumerate((("Nombre", self.v_name, 22), ("Tecla", self.v_trigger, 8))):
            ttk.Label(props, text=label).grid(row=0, column=col * 2, sticky="w", padx=(0, 4))
            ttk.Entry(props, textvariable=var, width=w).grid(row=0, column=col * 2 + 1, padx=(0, 10))
        ttk.Label(props, text="Modo").grid(row=0, column=4)
        ttk.Combobox(props, textvariable=self.v_mode, values=["toggle", "hold", "once"],
                     state="readonly", width=7).grid(row=0, column=5, padx=(4, 10))
        ttk.Label(props, text="Repeticiones (1, N o inf)").grid(row=0, column=6)
        ttk.Entry(props, textvariable=self.v_loop, width=6).grid(row=0, column=7, padx=4)
        self.v_speed = tk.StringVar(value=f"{macro.speed:g}")
        ttk.Label(props, text="Velocidad ×").grid(row=0, column=8, padx=(10, 0))
        ttk.Entry(props, textvariable=self.v_speed, width=5).grid(row=0, column=9, padx=4)

        body = ttk.Frame(self, padding=8)
        body.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(body, columns=("n", "type", "desc", "ms"), show="headings",
                                 selectmode="extended")
        for c, t, w in (("n", "#", 40), ("type", "Tipo", 70), ("desc", "Detalle", 360), ("ms", "ms", 70)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="w")
        self.tree.tag_configure("loop", background=current_palette().loop_bg)
        sb = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tree.bind("<Double-1>", lambda e: self.edit_step())
        self.tree.bind("<Delete>", lambda e: self.delete_steps())

        side = ttk.Frame(body, padding=(8, 0))
        side.pack(side="left", fill="y")
        n = 0
        for text, cmd in (("Añadir…", self.add_step), ("Editar…", self.edit_step),
                          ("Duplicar", self.duplicate_steps), ("Eliminar", self.delete_steps),
                          ("▲ Subir", lambda: self.move(-1)), ("▼ Bajar", lambda: self.move(1)),
                          ("Bucle desde aquí", self.set_loop_from),
                          ("Deshacer", self.undo), ("Rehacer", self.redo),
                          ("▶ Probar (simulación)", self.test_run)):
            ttk.Button(side, text=text, command=cmd).grid(
                row=n // 2, column=n % 2, sticky="ew", padx=2, pady=2)
            n += 1

        kb_box = ttk.LabelFrame(self, text="Teclado en pantalla: clic en una tecla para añadir un paso", padding=6)
        kb_box.pack(fill="x", padx=8)
        mode_bar = ttk.Frame(kb_box)
        mode_bar.pack(fill="x", pady=(0, 4))
        self.v_kbmode = tk.StringVar(value="tap")
        ttk.Label(mode_bar, text="Al pulsar una tecla:").pack(side="left")
        for text, val in (("Tocar (pulsar y soltar)", "tap"), ("Solo pulsar", "down"), ("Solo soltar", "up")):
            ttk.Radiobutton(mode_bar, text=text, value=val, variable=self.v_kbmode).pack(side="left", padx=6)
        self.kb = OnScreenKeyboard(kb_box, on_key=self.add_from_key)
        self.kb.pack(anchor="center")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._update_kb())

        foot = ttk.Frame(self, padding=8)
        foot.pack(fill="x")
        self.info = tk.StringVar()
        ttk.Label(foot, textvariable=self.info).pack(side="left")
        ttk.Button(foot, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(foot, text="Guardar cambios", command=self.save).pack(side="right", padx=6)
        self._snapshot = [Step(**s.__dict__) for s in macro.steps]
        self._orig = (macro.name, macro.trigger, macro.mode, macro.loop, macro.loop_from, macro.speed)
        self.refresh()
        self.grab_set()
        self.wait_window()

    # --- vista ---
    def refresh(self, select: list[int] | None = None) -> None:
        self.tree.delete(*self.tree.get_children())
        for i, s in enumerate(self.ed.steps):
            ms = {"wait": s.ms, "tap": s.hold_ms + s.ms}.get(s.type, "")
            tags = ("loop",) if i == self.macro.loop_from and self.macro.loop_from > 0 else ()
            self.tree.insert("", "end", iid=str(i), values=(i + 1, s.type, describe(s), ms), tags=tags)
        for i in select or []:
            if self.tree.exists(str(i)):
                self.tree.selection_add(str(i))
        self._update_kb()
        extra = f" · bucle desde el paso {self.macro.loop_from + 1}" if self.macro.loop_from else ""
        self.info.set(f"{len(self.ed.steps)} pasos · ~{duration_ms(self.macro):g} ms por pasada{extra}")

    def _update_kb(self) -> None:
        sel_steps = [self.ed.steps[i] for i in self._sel() if i < len(self.ed.steps)]
        self.kb.set_highlight(keys_used(self.ed.steps), keys_used(sel_steps))

    def add_from_key(self, key: str) -> None:
        """Clic en el teclado en pantalla: inserta un paso tras la selección (o al final)."""
        sel = self._sel()
        i = self.ed.add(step_for_key(key, self.v_kbmode.get()), sel[-1] + 1 if sel else None)
        self.refresh([i])
        self.tree.see(str(i))

    def _sel(self) -> list[int]:
        return sorted(int(i) for i in self.tree.selection())

    # --- acciones ---
    def add_step(self) -> None:
        sel = self._sel()
        d = StepDialog(self)
        if d.result:
            i = self.ed.add(d.result, sel[-1] + 1 if sel else None)
            self.refresh([i])

    def edit_step(self) -> None:
        sel = self._sel()
        if not sel:
            return
        d = StepDialog(self, self.ed.steps[sel[0]])
        if d.result:
            self.ed.replace(sel[0], d.result)
            self.refresh([sel[0]])

    def duplicate_steps(self) -> None:
        self.refresh(self.ed.duplicate(self._sel()))

    def delete_steps(self) -> None:
        self.ed.delete(self._sel())
        self.refresh()

    def move(self, delta: int) -> None:
        self.refresh(self.ed.move(self._sel(), delta))

    def set_loop_from(self) -> None:
        sel = self._sel()
        self.ed.set_loop_from(sel[0] if sel else 0)
        self.refresh(sel)

    def test_run(self) -> None:
        """Ejecuta la macro UNA vez en simulación (no envía nada) y muestra eventos con su tiempo."""
        import copy
        import threading
        from .backends import DryRunBackend
        from .engine import Runner
        try:
            speed = float(self.v_speed.get().replace(",", "."))
        except ValueError:
            speed = self.macro.speed
        m = copy.deepcopy(self.macro)
        m.loop, m.speed = False, max(0.1, min(speed, 10))
        be = DryRunBackend()
        win = tk.Toplevel(self)
        win.title(f"Prueba (simulación) — {m.name}")
        win.geometry("460x360")
        txt = tk.Text(win, font=("Consolas", 10), bg=current_palette().surface,
                      fg=current_palette().fg, insertbackground=current_palette().fg)
        txt.pack(fill="both", expand=True)
        txt.insert("end", "Ejecutando…\n")

        def work():
            Runner(m, be).run()     # solo toca el backend de simulación; la GUI se actualiza desde el hilo de Tk

        def poll():
            if not win.winfo_exists():
                return
            if th.is_alive():
                win.after(30, poll)
            else:
                show()

        def show():
            txt.delete("1.0", "end")
            for t, ev in zip(be.times, be.events):
                txt.insert("end", f"{t * 1000:9.1f} ms  {' '.join(str(x) for x in ev)}\n")
            if be.times:
                txt.insert("end", f"\nTotal: {be.times[-1] * 1000:.1f} ms, {len(be.events)} eventos")
            else:
                txt.insert("end", "(la macro no genera eventos)")

        th = threading.Thread(target=work, daemon=True)
        th.start()
        win.after(30, poll)

    def undo(self) -> None:
        self.ed.undo(); self.refresh()

    def redo(self) -> None:
        self.ed.redo(); self.refresh()

    def save(self) -> None:
        loop_txt = self.v_loop.get().strip().lower()
        try:
            loop: int | bool = (True if loop_txt in ("inf", "∞", "true")
                                else False if loop_txt in ("", "1", "false")
                                else int(loop_txt))
            if loop is not True and loop is not False and loop < 2:
                raise ValueError
        except ValueError:
            messagebox.showerror("Repeticiones", "Usa 1, un número ≥ 2 o 'inf'.", parent=self)
            return
        try:
            self.macro.speed = float(self.v_speed.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Velocidad", "Usa un número entre 0.1 y 10 (ej. 1 o 0.5).", parent=self)
            return
        self.macro.name = self.v_name.get().strip()
        self.macro.trigger = self.v_trigger.get().strip().lower() or None
        self.macro.mode = self.v_mode.get()
        self.macro.loop = loop
        try:
            self.macro.validate()
        except MacroError as e:
            messagebox.showerror("Macro inválida", str(e), parent=self)
            return
        self.saved = True
        self.destroy()

    def destroy(self) -> None:
        if not self.saved:  # cancelar: restaurar el estado original
            self.macro.steps[:] = self._snapshot
            (self.macro.name, self.macro.trigger, self.macro.mode,
             self.macro.loop, self.macro.loop_from, self.macro.speed) = self._orig
        super().destroy()
