import pytest

from macrolab.importers import load_amc
from macrolab.model import MacroError, load_macros

AMC = """<Root><DefaultMacro><Major>Demo</Major><Description>d</Description>
<GUIOption><RepeatType>0</RepeatType></GUIOption><KeyUp><Syntax></Syntax></KeyUp>
<KeyDown><Syntax>KeyDown 22 1
Delay 50 ms
KeyUp 22 1
KeyDown 44 1
KeyUp 44 1
Foo 1 2</Syntax></KeyDown><Software>Test</Software></DefaultMacro></Root>"""


def test_amc_import(tmp_path):
    p = tmp_path / "m.amc"
    p.write_text(AMC, encoding="utf-8")
    macros, warns = load_amc(p)
    m = macros[0]
    assert m.name == "Demo" and m.description.startswith("[Test]")
    assert [(s.type, s.key, s.ms) for s in m.steps] == [
        ("down", "s", 0), ("wait", None, 50.0), ("up", "s", 0),
        ("down", "space", 0), ("up", "space", 0)]
    assert len(warns) == 1 and "Foo" in warns[0]
    assert load_macros(p)[0].name == "Demo"  # load_macros entiende .amc


def test_amc_rejects_entities(tmp_path):
    p = tmp_path / "x.amc"
    p.write_text('<!DOCTYPE r [<!ENTITY a "b">]><Root/>')
    with pytest.raises(MacroError):
        load_amc(p)


def test_amc_mouse_and_goto_loop(tmp_path):
    from macrolab.backends import DryRunBackend
    from macrolab.engine import Runner
    p = tmp_path / "r.amc"
    p.write_text("""<Root><DefaultMacro><Major>M</Major><GUIOption><RepeatType>1</RepeatType></GUIOption>
<KeyDown><Syntax>LeftDown 1
MoveR 1 0
Delay 0 ms
MoveR 0 -2
Goto 2</Syntax></KeyDown></DefaultMacro></Root>""")
    (m,), warns = load_amc(p)
    assert not warns and m.mode == "hold" and m.loop is True and m.loop_from == 1
    assert m.steps[0].key == "mouse_left"
    # LeftDown solo en la primera pasada; después se repite desde la línea 2
    import threading, time
    b = DryRunBackend(); r = Runner(m, b); r.start(); time.sleep(0.05); r.stop()
    kinds = [e[0] for e in b.events]
    assert kinds.count("mouse_down") == 1 and kinds.count("mouse_move") > 2
    assert b.events[-1] == ("mouse_up", "left")


def test_amc_wheel_and_delay_without_unit(tmp_path):
    p = tmp_path / "w.amc"
    p.write_text("<Root><DefaultMacro><Major>W</Major><KeyDown><Syntax>WheelDown 1\nDelay 64\nKeyDown 6 1\nKeyUp 6 1</Syntax></KeyDown></DefaultMacro></Root>")
    (m,), warns = load_amc(p)
    assert not warns
    assert [(s.type, s.dy, s.ms, s.key) for s in m.steps] == [
        ("scroll", -1, 0, None), ("wait", 0, 64.0, None), ("down", 0, 0, "c"), ("up", 0, 0, "c")]
