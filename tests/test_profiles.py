import json
import time

import pytest

from macrolab.active_window import Window
from macrolab.backends import DryRunBackend
from macrolab.model import MacroError
from macrolab.profiles import ProfileManager, is_profile_file, load_profiles, save_profiles

M = lambda name, trig, ms=5000: {"name": name, "trigger": trig, "mode": "toggle", "loop": True,
                                  "steps": [{"type": "down", "key": "w"}, {"type": "wait", "ms": ms}]}

CFG = {"profiles": [
    {"name": "Notepad", "process": "notepad.exe", "macros": [M("a", "f6")]},
    {"name": "Cualquier chrome con docs", "process": "chrome.exe", "title_contains": "docs", "macros": [M("b", "f6")]},
    {"name": "Global", "macros": [M("g", "f7")]},
]}


@pytest.fixture
def pset(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps(CFG))
    assert is_profile_file(p)
    return load_profiles(p)


def test_select_rules(pset):
    sel = lambda proc, title="": pset.select(Window(proc, title)).name
    assert sel("NOTEPAD.EXE", "x") == "Notepad"                       # sin distinguir mayúsculas
    assert sel("chrome.exe", "Mis Docs - Chrome") == "Cualquier chrome con docs"
    assert sel("chrome.exe", "YouTube") == "Global"                   # process coincide, título no
    assert pset.select(None).name == "Global"                         # ventana desconocida
    assert load_profiles_no_default().select(Window("x", "y")) is None


def load_profiles_no_default():
    from macrolab.profiles import ProfileSet, Profile
    return ProfileSet([Profile("solo", [], process="a.exe")])


def test_switch_stops_previous_profile_macros(pset):
    win = [Window("notepad.exe", "n")]
    b = DryRunBackend()
    changes = []
    pm = ProfileManager(pset, b, get_window=lambda: win[0], on_change=lambda p: changes.append(p.name))
    assert pm.current.name == "Notepad" and pm.lookup("<f6>") == "a" and pm.lookup("<f7>") is None
    pm.press("a"); time.sleep(0.05)
    win[0] = Window("otro.exe", "")
    assert pm.refresh() and pm.current.name == "Global"
    assert b.events[-1] == ("key_up", "w")        # soltó lo que dejó pulsado
    assert pm.lookup("<f6>") is None and pm.lookup("<f7>") == "g"
    assert not pm.refresh() and changes == ["Notepad", "Global"]
    pm.press("a"); pm.release("a")                # macro de otro perfil: se ignora sin error
    pm.close()


def test_bind_macros_file_and_errors(tmp_path):
    amc = tmp_path / "m.amc"
    amc.write_text("<Root><DefaultMacro><Major>Mantle</Major><KeyDown><Syntax>KeyDown 22 1\nKeyUp 22 1</Syntax></KeyDown></DefaultMacro></Root>")
    cfg = tmp_path / "p.json"
    cfg.write_text(json.dumps({"profiles": [{"name": "X", "process": "x.exe",
                                             "macros_file": "m.amc", "bind": {"Mantle": "f8"}}]}))
    ps = load_profiles(cfg)
    assert ps.get("X").macros[0].trigger == "f8"
    save_profiles(tmp_path / "out.json", ps)
    assert load_profiles(tmp_path / "out.json").get("X").process == "x.exe"
    for bad in ({"profiles": [{"name": "X", "bind": {"nope": "f1"}}]},
                {"profiles": [{"name": "X", "macros_file": "../../etc/passwd"}]},
                {"profiles": [{"name": "X"}, {"name": "X"}]},
                {"profiles": [{"process": "a"}]}):
        cfg.write_text(json.dumps(bad))
        with pytest.raises(MacroError):
            load_profiles(cfg)
