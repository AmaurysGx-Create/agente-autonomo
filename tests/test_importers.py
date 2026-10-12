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
