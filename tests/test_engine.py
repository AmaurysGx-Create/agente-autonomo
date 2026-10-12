import json
import time

import pytest

from gx_keybinds.backends import DryRunBackend
from gx_keybinds.engine import Manager, Runner
from gx_keybinds.model import Macro, MacroError, Step, load_macros, save_macros


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


def test_recorder_builds_steps_with_waits():
    from gx_keybinds.recorder import Recorder
    r = Recorder(record_moves=True)
    r.add("key_down", "a", t=0.0)
    r.add("key_up", "a", t=0.05)
    r.add("move", 3, 1, t=0.10)
    r.add("move", 2, 2, t=0.10)
    r.add("mouse_down", "left", t=0.30)
    m = r.to_macro("rec")
    assert [(s.type, s.key) for s in m.steps if s.type in ("down", "up")] == \
        [("down", "a"), ("up", "a"), ("down", "mouse_left")]
    assert any(s.type == "move" and (s.dx, s.dy) == (5, 3) for s in m.steps)
    assert any(s.type == "wait" and s.ms == 200.0 for s in m.steps)


def test_recorded_mouse_buttons_replay_as_mouse_events():
    b = DryRunBackend()
    Runner(Macro("m", [Step("down", key="mouse_left"), Step("up", key="mouse_left")]), b).run()
    assert b.events == [("mouse_down", "left"), ("mouse_up", "left")]


def test_mouse_steps_from_json():
    b = DryRunBackend()
    m = load_macros("examples/mouse.json")[0]
    for s in m.steps:
        if s.type == "wait":
            s.ms = 0
    Runner(m, b).run()
    assert b.events == [
        ("mouse_down", "left"), ("mouse_up", "left"), ("mouse_down", "left"), ("mouse_up", "left"),
        ("mouse_move", 100, 0), ("mouse_down", "right"), ("mouse_up", "right"), ("scroll", 0, -3)]


def test_mouse_released_on_stop_and_moveto():
    b = DryRunBackend()
    r = Runner(Macro("m", [Step("moveto", dx=10, dy=20), Step("down", key="mouse_left"), Step("wait", ms=5000)]), b)
    r.start(); time.sleep(0.05); r.stop()
    assert b.events[0] == ("mouse_moveto", 10, 20) and b.events[-1] == ("mouse_up", "left")


def test_duplicate_triggers_detected():
    m = Manager([Macro("a", trigger="F6"), Macro("b", trigger="f6"), Macro("c", trigger="f7")],
                DryRunBackend())
    assert m.duplicate_triggers() == ["<f6>"]


def test_speed_scales_waits_and_validates():
    import time
    b = DryRunBackend()
    m = Macro("m", [Step("wait", ms=200), Step("down", key="a")], speed=4.0)
    t = time.perf_counter(); Runner(m, b).run(); dt = time.perf_counter() - t
    assert dt < 0.15 and b.events == [("key_down", "a"), ("key_up", "a")]
    for bad in (0.01, 50):
        with pytest.raises(MacroError):
            Macro("x", speed=bad).validate()
    assert Macro.from_dict(m.to_dict()).speed == 4.0
