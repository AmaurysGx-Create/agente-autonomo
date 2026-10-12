import time

from gx_keybinds import engine
from gx_keybinds.backends import DryRunBackend
from gx_keybinds.engine import Runner
from gx_keybinds.model import Macro, Step
from gx_keybinds.system_tweaks import TweakManager


class FakeApi:
    def __init__(self):
        self.kb, self.mouse, self.timer_active = (1, 20), (6, 10, 1), False
    def get_keyboard(self): return self.kb
    def set_keyboard(self, d, s): self.kb = (d, s)
    def get_mouse(self): return self.mouse
    def set_mouse(self, a, b, c): self.mouse = (a, b, c)
    def timer_begin(self): self.timer_active = True
    def timer_end(self): self.timer_active = False


def test_enable_disable_restores_originals():
    engine.SPIN_S = 0.003
    api, store, saved = FakeApi(), {}, []
    tm = TweakManager(api, store, lambda: saved.append(1))
    assert [t.id for t in tm.tweaks] == ["keys", "timer", "precise", "mouse"]   # sin plan de energía
    assert not any(t.is_on() for t in tm.tweaks)
    for t in tm.tweaks:
        assert tm.set(t.id, True) is True
    assert api.kb == (0, 31) and api.mouse[2] == 0 and api.timer_active and engine.SPIN_S >= 0.05
    for t in tm.tweaks:
        assert tm.set(t.id, False) is False
    assert api.kb == (1, 20) and api.mouse == (6, 10, 1) and not api.timer_active and engine.SPIN_S == 0.003
    assert saved and store["precise"] is False


def test_enable_twice_keeps_first_backup_and_restore_all():
    api = FakeApi()
    tm = TweakManager(api, {})
    tm.set("keys", True); tm.set("keys", True)       # el 2º no debe pisar el respaldo con el valor "rápido"
    tm.restore_all()
    assert api.kb == (1, 20)


def test_precise_preference_applied_at_startup_and_sub_ms_waits():
    engine.SPIN_S = 0.003
    tm = TweakManager(FakeApi(), {"precise": True})
    assert tm.get("precise").is_on()
    b = DryRunBackend()
    m = Macro("m", [Step("down", key="a"), Step("wait", ms=0.01), Step("up", key="a")])   # 0.01 ms
    t = time.perf_counter(); Runner(m, b).run(); dt = time.perf_counter() - t
    assert dt < 0.05 and [e[0] for e in b.events] == ["key_down", "key_up"]
    engine.SPIN_S = 0.003
