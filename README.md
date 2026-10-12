# Gx Keybinds

Motor de macros personal (teclado/ratón), escrito en Python para practicar programación.
Inspirado en herramientas tipo Keyran/AutoHotkey, pero con formato propio y abierto (JSON).

> Uso personal y de aprendizaje. Muchos juegos online (anti-cheat/ToS) prohíben macros
> incluso en modos de práctica; úsalo en software offline o de pruebas bajo tu responsabilidad.

## Uso
```
pip install -r requirements.txt
python -m gx_keybinds check examples/basic.json
python -m gx_keybinds run examples/basic.json --dry-run   # simula, no envía nada
python -m gx_keybinds run examples/basic.json             # real; F12 = pánico (detiene todo)
python -m gx_keybinds gui   # incluye botón ● Grabar (F12 o ■ Detener para terminar)
python -m gx_keybinds record mi_macro -o mi_macro.json --trigger f6   # F12 termina la grabación
```

## Formato de macro
Pasos: `down`, `up`, `tap` (key, hold_ms, ms), `click` (button, count, hold_ms, ms),
`move` (dx, dy), `moveto` (x en dx, y en dy), `scroll` (dx, dy), `wait` (ms), `text` (value). Disparador: `trigger` + `mode`
(`toggle` | `hold` | `once`) y `loop` (false / true / N). Ver `examples/basic.json`.

Tests: `pip install pytest && pytest`

## Importar macros descargadas (.amc)
```
python -m gx_keybinds import macro.amc -o macro.json --trigger f6
python -m gx_keybinds run macro.amc --dry-run --now "Nombre de la macro"   # también se carga directo
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

## Perfiles por programa
Un archivo de perfiles agrupa macros y las activa según la ventana en primer plano
(ver `examples/profiles.json`):
```
python -m gx_keybinds window                       # te dice qué poner en "process" / "title_contains"
python -m gx_keybinds check examples/profiles.json
python -m gx_keybinds run examples/profiles.json --dry-run
```
Cada perfil tiene `process` (ej. `notepad.exe`) y/o `title_contains`; un perfil sin ninguno es el
**por defecto** (se usa si ningún otro coincide). Puede incluir `macros` en línea, `macros_file`
(un `.json` o un `.amc` descargado, en la misma carpeta o subcarpeta) y `bind` para asignar
teclas: `{"Mantle Jump macro": "f6"}`. Al cambiar de ventana se detienen las macros del perfil anterior.
En Windows la detección de ventana es nativa; en Linux requiere `xdotool`; macOS aún no.
En la GUI, abrir un archivo de perfiles muestra un selector de perfil y la casilla «Automático».

## Instalador para Windows
Necesitas Python 3.10+ y, para el instalador, [Inno Setup 6](https://jrsoftware.org/isinfo.php).
```
packaging\build_windows.bat
```
Genera `dist\GxKeybinds\GxKeybinds.exe` (PyInstaller, sin consola) y, si Inno Setup está instalado,
`dist\GxKeybinds-Setup-<versión>.exe`: instalación por usuario (sin administrador), acceso en el menú
Inicio, icono opcional en el escritorio y desinstalador. También se construye en GitHub Actions
(`.github/workflows/windows-installer.yml`, manual o al subir un tag `v*`; el instalador queda como artefacto).

Icono: `assets/icon.ico` (exe e instalador) y `gx_keybinds/icon.png` (ventana). Para cambiarlo, reemplaza esos archivos.

Notas: un programa que envía teclas/ratón no puede controlar ventanas ejecutadas como administrador
salvo que Gx Keybinds también se ejecute como administrador. Los ejecutables de PyInstaller a veces
los marca el antivirus como falso positivo: añade la carpeta de instalación a las exclusiones si pasa.

## Modo oscuro
Botón **🌙 Modo oscuro / ☀ Modo claro** en la barra inferior de la GUI. La elección se guarda en
`%APPDATA%\GxKeybinds\settings.json` (en Linux `~/.config/gx_keybinds/`); la primera vez sigue el
tema de aplicaciones de Windows.
