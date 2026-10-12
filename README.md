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
python -m macrolab gui   # incluye botón ● Grabar (F12 o ■ Detener para terminar)
python -m macrolab record mi_macro -o mi_macro.json --trigger f6   # F12 termina la grabación
```

## Formato de macro
Pasos: `down`, `up`, `tap` (key, hold_ms, ms), `click` (button, count, hold_ms, ms),
`move` (dx, dy), `moveto` (x en dx, y en dy), `scroll` (dx, dy), `wait` (ms), `text` (value). Disparador: `trigger` + `mode`
(`toggle` | `hold` | `once`) y `loop` (false / true / N). Ver `examples/basic.json`.

Tests: `pip install pytest && pytest`

## Importar macros descargadas (.amc)
```
python -m macrolab import macro.amc -o macro.json --trigger f6
python -m macrolab run macro.amc --dry-run --now "Nombre de la macro"   # también se carga directo
```
Soporta `KeyDown`/`KeyUp`/`Delay` (códigos USB HID). Lo no soportado se omite con aviso;
nunca se ejecuta código del archivo.

Ratón: `click` (left/right/middle, count), `down`/`up` con `key: "mouse_left"` etc.
(para mantener pulsado), `move`/`moveto`, `scroll`. Ver `examples/mouse.json`.

`.amc` también entiende `LeftDown`, `MoveR dx dy`, `WheelDown N` y `Goto N` (bucle). Macros con `loop_from`
repiten desde ese paso tras la primera pasada.

## Editor visual de pasos
En la GUI: **Nueva** o selecciona una macro y **Editar pasos…** (doble clic en un paso para editarlo).
Añadir/editar/duplicar/eliminar, subir/bajar, deshacer/rehacer, «Bucle desde aquí» (`loop_from`),
y propiedades (nombre, tecla, modo, repeticiones). Cancelar descarta los cambios.
