# MacroLab

Motor de macros personal (teclado/ratón), escrito en Python para practicar programación.
Inspirado en herramientas tipo Keyran/AutoHotkey, pero con formato propio y abierto (JSON).

> Uso personal y de aprendizaje. Muchos juegos online (anti-cheat/ToS) prohíben macros
> incluso en modos de práctica; úsalo en software offline o de pruebas bajo tu responsabilidad.

## Uso
```
pip install -r requirements.txt
python -m macrolab check examples/basic.json
python -m macrolab run examples/basic.json --dry-run   # simula, no envía nada
python -m macrolab run examples/basic.json             # real; F12 = pánico (detiene todo)
python -m macrolab gui
```

## Formato de macro
Pasos: `down`, `up`, `tap` (key, hold_ms, ms), `click` (button, count, hold_ms, ms),
`move` (dx, dy), `wait` (ms), `text` (value). Disparador: `trigger` + `mode`
(`toggle` | `hold` | `once`) y `loop` (false / true / N). Ver `examples/basic.json`.

Tests: `pip install pytest && pytest`
