from gx_keybinds.importers import _HID
from gx_keybinds.keyboard_layout import (WIDTH_KEYS, all_keys, key_rects, keys_used, step_for_key,
                                         MOUSE_KEYS)
from gx_keybinds.model import Step


def test_keys_unique_and_consistent_with_importer():
    keys = all_keys()
    assert len(keys) == len(set(keys))
    mouse = {k for _, k, _ in MOUSE_KEYS}
    valid = set(_HID.values()) | {"menu"} | mouse
    assert [k for k in keys if k not in valid] == []          # mismos nombres que el importador .amc
    assert {"space", "w", "shift", "f12", "up"} <= set(keys)


def test_rects_do_not_overlap_and_fit():
    rects = key_rects(36, 3)
    for i, (_, _, x, y, w, h) in enumerate(rects):
        assert w > 0 and h > 0 and x >= 0
        for _, _, x2, y2, w2, h2 in rects[i + 1:]:
            assert x + w <= x2 or x2 + w2 <= x or y + h <= y2 or y2 + h2 <= y
    assert max(x + w for _, _, x, _, w, _ in rects) <= WIDTH_KEYS * 36


def test_step_for_key_and_keys_used():
    assert step_for_key("a").type == "tap" and step_for_key("a", "down").type == "down"
    assert step_for_key("a", "up", ).key == "a"
    c = step_for_key("mouse_right")
    assert (c.type, c.button) == ("click", "right")
    assert step_for_key("mouse_left", "down").key == "mouse_left"
    assert step_for_key("wheel_down").dy == -1
    for s in (step_for_key(k, m) for k in all_keys() for m in ("tap", "down", "up")):
        s.validate()                                           # todos los pasos generados son válidos
    steps = [Step("tap", key="a"), Step("click", button="left"), Step("scroll", dy=-2), Step("wait", ms=5)]
    assert keys_used(steps) == {"a", "mouse_left", "wheel_down"}
