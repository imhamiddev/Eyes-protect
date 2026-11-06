from eyecare.core import winapi


def test_import_and_noop_behaviour_off_windows():
    if winapi.IS_WINDOWS:
        return
    assert winapi.idle_seconds() == 0.0
    assert winapi.set_gamma_ramp([[0] * 256] * 3) is False
    assert winapi.reset_gamma() is False
    assert winapi.set_autostart(True, "x") is False
    assert winapi.is_autostart_enabled() is False
    assert winapi.system_uses_light_theme() is False
    assert winapi.set_system_light_theme(True) is False
