# PyInstaller: `pyinstaller packaging/gx_keybinds.spec --noconfirm` (desde la raíz del repo)
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

a = Analysis(
    [os.path.join(SPECPATH, "gx_keybinds_gui.py")],
    pathex=[ROOT],
    datas=[(os.path.join(ROOT, "examples"), "examples")],
    hiddenimports=["pynput.keyboard._win32", "pynput.mouse._win32"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="GxKeybinds", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="GxKeybinds")
