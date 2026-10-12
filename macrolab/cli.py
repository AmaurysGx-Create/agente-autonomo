"""CLI: macrolab run|check|list|gui."""
from __future__ import annotations

import argparse
import sys

from .backends import DryRunBackend
from .engine import Manager, Runner
from .model import MacroError, load_macros


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="macrolab", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("run", "check", "list"):
        sp = sub.add_parser(name)
        sp.add_argument("file")
        if name == "run":
            sp.add_argument("--dry-run", action="store_true", help="no envía entrada real")
            sp.add_argument("--panic", default="f12", help="tecla que detiene todo")
            sp.add_argument("--now", metavar="NAME", help="ejecuta una macro ya (sin hotkey)")
    sub.add_parser("gui")
    rp = sub.add_parser("record", help="graba una macro en vivo")
    rp.add_argument("name")
    rp.add_argument("-o", "--output", required=True, help="archivo .json de salida")
    rp.add_argument("--stop", default="f12", help="tecla para terminar la grabación")
    rp.add_argument("--moves", action="store_true", help="grabar también movimiento del ratón")
    rp.add_argument("--trigger", help="tecla de activación a guardar, p. ej. f6")
    rp.add_argument("--mode", default="once", choices=["toggle", "hold", "once"])
    a = p.parse_args(argv)

    if a.cmd == "gui":
        from .gui import main as gui_main
        gui_main()
        return 0

    if a.cmd == "record":
        from .recorder import record_live
        from .model import save_macros
        print(f"Grabando '{a.name}'... pulsa {a.stop} para terminar.")
        m = record_live(a.name, stop_key=a.stop, record_moves=a.moves)
        m.trigger, m.mode = a.trigger, a.mode
        save_macros(a.output, [m])
        print(f"Guardada: {len(m.steps)} pasos -> {a.output}")
        return 0

    try:
        macros = load_macros(a.file)
    except (MacroError, OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if a.cmd == "check":
        print(f"OK: {len(macros)} macro(s) válidas")
        return 0
    if a.cmd == "list":
        for m in macros:
            print(f"{m.name:24} trigger={m.trigger} mode={m.mode} loop={m.loop} pasos={len(m.steps)}")
        return 0

    if a.dry_run:
        backend = DryRunBackend(echo=True)
    else:
        from .backends import PynputBackend
        backend = PynputBackend()

    if a.now:
        by_name = {m.name: m for m in macros}
        if a.now not in by_name:
            print(f"no existe la macro {a.now!r}", file=sys.stderr)
            return 1
        r = Runner(by_name[a.now], backend)
        r.run()
        return 0

    from .hotkeys import listen
    mgr = Manager(macros, backend)
    print(f"Escuchando {len(macros)} macro(s). Pánico: {a.panic}. Ctrl+C para salir.")
    try:
        listen(mgr, panic=a.panic)
    except KeyboardInterrupt:
        mgr.stop_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
