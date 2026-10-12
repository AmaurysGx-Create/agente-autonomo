@echo off
REM Construye el .exe (PyInstaller) y el instalador (Inno Setup). Ejecutar desde la raiz del repo:
REM   packaging\build_windows.bat
setlocal
cd /d "%~dp0\.."
python -m venv .venv-build || goto :err
call .venv-build\Scripts\activate.bat
python -m pip install -q --upgrade pip pyinstaller -r requirements.txt || goto :err
for /f %%v in ('python -c "import gx_keybinds;print(gx_keybinds.__version__)"') do set VER=%%v
pyinstaller packaging\gx_keybinds.spec --noconfirm --clean || goto :err
set ISCC=
where iscc >nul 2>nul && set ISCC=iscc
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set ISCC="%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo.
  echo Listo el .exe en dist\GxKeybinds\GxKeybinds.exe
  echo Para crear el instalador instala Inno Setup 6 ^(https://jrsoftware.org/isinfo.php^) y vuelve a ejecutar.
  exit /b 0
)
%ISCC% /DMyAppVersion=%VER% packaging\installer.iss || goto :err
echo.
echo Instalador: dist\GxKeybinds-Setup-%VER%.exe
exit /b 0
:err
echo ERROR en la construccion.
exit /b 1
