from gx_keybinds.settings import load_settings, save_settings
from gx_keybinds.themes import DARK, LIGHT


def test_settings_roundtrip_and_bad_file(tmp_path):
    p = tmp_path / "sub" / "settings.json"
    assert load_settings(p) == {}                       # no existe
    save_settings({"dark": True}, p)
    assert load_settings(p) == {"dark": True}
    p.write_text("{no json")
    assert load_settings(p) == {}                       # corrupto -> valores por defecto
    p.write_text("[1,2]")
    assert load_settings(p) == {}


def test_palettes_are_distinct_hex():
    import re
    for pal in (LIGHT, DARK):
        assert all(re.fullmatch(r"#[0-9a-f]{6}", v) for v in pal.__dict__.values())
    assert LIGHT.bg != DARK.bg and LIGHT.fg != DARK.fg
