import pytest

from gx_keybinds.tray import ICON_PATH, make_tray


def test_icon_exists_and_handlers_invoked():
    assert ICON_PATH.exists()
    calls = []
    names = ("show", "toggle", "editor", "settings", "exit")
    tray = make_tray({n: (lambda n=n: calls.append(n)) for n in names}, is_running=lambda: False)
    if tray is None:
        pytest.skip("pystray no disponible en este entorno")
    for n in names:
        tray.invoke(n)
    assert calls == list(names)
