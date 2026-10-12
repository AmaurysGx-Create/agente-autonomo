@echo off
REM Prueba rapida de Gx Keybinds en Windows (sin instalador). Doble clic o: run_gui.bat
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  python -m venv .venv || (echo Instala Python 3.10+ desde python.org ^(marca "Add to PATH"^) & pause & exit /b 1)
  .venv\Scripts\python -m pip install -q -r requirements.txt || (pause & exit /b 1)
)
.venv\Scripts\python -m gx_keybinds gui
