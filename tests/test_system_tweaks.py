import pytest

from gx_keybinds.system_tweaks import HIGH_PERF_GUID, TweakError, TweakManager


class FakeApi:
    def __init__(self):
        self.kb, self.mouse, self.power, self.timer_active = (1, 20), (6, 10, 1), "aaaa1111-0000-0000-0000-000000000000", False
    def get_keyboard(self): return self.kb
    def set_keyboard(self, d, s): self.kb = (d, s)
    def get_mouse(self): return self.mouse
    def set_mouse(self, a, b, c): self.mouse = (a, b, c)
    def timer_begin(self): self.timer_active = True
    def timer_end(self): self.timer_active = False
    def get_power_scheme(self): return self.power
    def set_power_scheme(self, g): self.power = g


def test_enable_disable_restores_originals():
    api, store, saved = FakeApi(), {}, []
    tm = TweakManager(api, store, lambda: saved.append(1))
    assert not any(t.is_on() for t in tm.tweaks)
    for tid in ("keys", "mouse", "timer", "power"):
        assert tm.set(tid, True) is True
    assert api.kb == (0, 31) and api.mouse[2] == 0 and api.timer_active and api.power == HIGH_PERF_GUID
    for tid in ("keys", "mouse", "timer", "power"):
        assert tm.set(tid, False) is False
    assert api.kb == (1, 20) and api.mouse == (6, 10, 1) and not api.timer_active
    assert api.power == "aaaa1111-0000-0000-0000-000000000000" and saved


def test_enable_twice_keeps_first_backup_and_restore_all():
    api, tm = FakeApi(), None
    tm = TweakManager(api, {})
    tm.set("keys", True); tm.set("keys", True)       # el 2º no debe pisar el respaldo con el valor "rápido"
    tm.set("power", True)
    tm.restore_all()
    assert api.kb == (1, 20) and api.power.startswith("aaaa1111")


def test_power_disable_without_backup_errors():
    api = FakeApi(); api.power = HIGH_PERF_GUID       # ya estaba en alto rendimiento antes de abrir la app
    with pytest.raises(TweakError):
        TweakManager(api, {}).set("power", False)
