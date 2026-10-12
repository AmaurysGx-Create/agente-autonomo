import sys
from types import SimpleNamespace as NS

from gx_keybinds import keynames as kn


def test_numpad_names_and_vk():
    assert kn.numpad_vk("num5") == (0x65 if sys.platform == "win32" else 0xFFB5)
    assert kn.numpad_vk("nope") is None and "num_add" in kn.NUMPAD and "a" not in kn.NUMPAD


def test_name_from_pynput_distinguishes_numpad():
    vk5 = kn.numpad_vk("num5")
    assert kn.name_from_pynput(NS(vk=vk5, char="5")) == "num5"      # numpad
    assert kn.name_from_pynput(NS(vk=0x35, char="5")) == "5"        # fila de números
    assert kn.name_from_pynput(NS(name="f12")) == "f12"
    assert kn.name_from_pynput(NS(vk=None, char="A")) == "a"
