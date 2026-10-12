import pytest

from gx_keybinds.editor_model import StepEditor, build_step, describe, duration_ms, step_values
from gx_keybinds.model import Macro, MacroError, Step


def mk():
    return Macro("m", [Step("tap", key="a"), Step("wait", ms=100), Step("tap", key="b"), Step("tap", key="c")])


def keys(ed):
    return [s.key or s.type for s in ed.steps]


def test_build_step_validates():
    s = build_step("click", {"button": "right", "count": "3", "hold_ms": "10", "ms": "5"})
    assert (s.button, s.count, s.hold_ms, s.ms) == ("right", 3, 10.0, 5.0)
    assert step_values(s)["count"] == "3"
    for t, v in [("tap", {"key": "a", "hold_ms": "x"}), ("click", {"button": "foo"}),
                 ("nada", {}), ("click", {"count": "0"})]:
        with pytest.raises(MacroError):
            build_step(t, v)
    assert build_step("text", {"value": " hola "}).value == " hola "
    assert build_step("scroll", {"dy": "-2"}).dy == -2


def test_add_delete_duplicate_move_undo_redo():
    ed = StepEditor(mk())
    assert ed.add(Step("tap", key="z"), 1) == 1 and keys(ed)[1] == "z"
    ed.delete([1]); assert keys(ed) == ["a", "wait", "b", "c"]
    assert ed.duplicate([0, 2]) == [3, 4] and keys(ed) == ["a", "wait", "b", "a", "b", "c"]
    ed.undo(); assert keys(ed) == ["a", "wait", "b", "c"]
    assert ed.move([2, 3], -1) == [1, 2] and keys(ed) == ["a", "b", "c", "wait"]
    assert ed.move([0], -1) == [0] and keys(ed) == ["a", "b", "c", "wait"]  # límite: no cambia
    ed.undo(); ed.redo(); assert keys(ed) == ["a", "b", "c", "wait"]
    assert not StepEditor(mk()).undo()


def test_loop_from_clamped_on_delete():
    m = mk(); m.loop_from = 3
    ed = StepEditor(m); ed.delete([2, 3])
    assert m.loop_from == 1
    m.validate()


def test_describe_and_duration():
    m = mk()
    assert duration_ms(m) == 20 + 100 + 20 + 20
    assert all(describe(s) for s in m.steps)
    assert describe(Step("move", dx=3, dy=-2)) == "Mover (+3, -2)"
