from eyecare.core.colortemp import (
    NEUTRAL_KELVIN,
    build_ramp,
    channel_multipliers,
    kelvin_to_strength,
    strength_to_kelvin,
)


def test_neutral_is_identity():
    r, g, b = channel_multipliers(NEUTRAL_KELVIN, 1.0)
    assert (round(r, 3), round(g, 3), round(b, 3)) == (1.0, 1.0, 1.0)


def test_warm_reduces_blue_most():
    r, g, b = channel_multipliers(3000, 1.0)
    assert r >= g > b


def test_brightness_is_clamped():
    r, _, _ = channel_multipliers(NEUTRAL_KELVIN, 0.0)
    assert r >= 0.3 - 1e-9


def test_strength_mapping_roundtrip():
    assert strength_to_kelvin(0) == NEUTRAL_KELVIN
    assert strength_to_kelvin(100) == 1900
    for s in (0, 25, 50, 75, 100):
        assert kelvin_to_strength(strength_to_kelvin(s)) == s


def test_ramp_shape_and_monotonic():
    ramp = build_ramp((1.0, 0.8, 0.5))
    assert len(ramp) == 3 and all(len(c) == 256 for c in ramp)
    assert ramp[0][255] == 65535
    assert ramp[2][255] < ramp[1][255] < ramp[0][255]
    assert all(a <= b for a, b in zip(ramp[1], ramp[1][1:]))
