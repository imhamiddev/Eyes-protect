import json

from eyecare.core.config import Settings, load_settings, save_settings, settings_from_dict


def test_defaults():
    s = Settings()
    assert s.rule202020.interval_min == 20
    assert s.rule202020.break_seconds == 20
    assert s.general.theme == "dark"


def test_roundtrip(tmp_path):
    path = tmp_path / "s.json"
    s = Settings()
    s.night_light.strength = 77
    s.general.language = "fa"
    save_settings(s, path)
    loaded = load_settings(path)
    assert loaded.night_light.strength == 77
    assert loaded.general.language == "fa"


def test_missing_file_gives_defaults(tmp_path):
    assert load_settings(tmp_path / "nope.json") == Settings()


def test_corrupt_file_gives_defaults(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    assert load_settings(path) == Settings()


def test_wrong_types_and_unknown_keys_ignored():
    s = settings_from_dict(
        {"blink": {"interval_min": "soon", "enabled": False, "bogus": 1}, "zzz": {}}
    )
    assert s.blink.interval_min == 5
    assert s.blink.enabled is False


def test_bool_is_not_accepted_as_int():
    s = settings_from_dict({"blink": {"interval_min": True}})
    assert s.blink.interval_min == 5


def test_partial_file_keeps_other_defaults(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"hydration": {"interval_min": 30}}), encoding="utf-8")
    s = load_settings(path)
    assert s.hydration.interval_min == 30
    assert s.rule202020.interval_min == 20
