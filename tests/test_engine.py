import json
import time

import pytest

from macrolab.backends import DryRunBackend
from macrolab.engine import Manager, Runner
from macrolab.model import Macro, MacroError, Step, load_macros, save_macros


def test_runs_steps_in_order():
    b = DryRunBackend()
    Runner(Macro("m", [Step("tap", key="a", hold_ms=0), Step("click", button="left", count=2, hold_ms=0)]), b).run()
    assert [e[0] for e in b.events] == ["key_down", "key_up"] + ["mouse_down", "mouse_up"] * 2


def test_finite_loop():
    b = DryRunBackend()
    Runner(Macro("m", [Step("down", key="x"), Step("up", key="x")], loop=3), b).run()
    assert len(b.events) == 6


def test_stop_releases_held_keys():
    b = DryRunBackend()
    r = Runner(Macro("m", [Step("down", key="w"), Step("wait", ms=5000)]), b)
    r.start(); time.sleep(0.05); r.stop()
    assert not r.running and b.events[-1] == ("key_up", "w")


def test_toggle_and_hold_modes():
    b = DryRunBackend()
    m = Manager([Macro("t", [Step("wait", ms=10)], mode="toggle", loop=True),
                 Macro("h", [Step("wait", ms=10)], mode="hold", loop=True)], b)
    m.press("t"); assert m.runners["t"].running
    m.press("t"); assert not m.runners["t"].running
    m.press("h"); assert m.runners["h"].running
    m.release("h"); assert not m.runners["h"].running


def test_validation_and_roundtrip(tmp_path):
    with pytest.raises(MacroError):
        Macro.from_dict({"name": "x", "steps": [{"type": "tap"}]})
    with pytest.raises(MacroError):
        Macro.from_dict({"name": "x", "mode": "raro"})
    p = tmp_path / "m.json"
    ms = load_macros("examples/basic.json")
    save_macros(p, ms)
    assert [m.to_dict() for m in load_macros(p)] == [m.to_dict() for m in ms]
