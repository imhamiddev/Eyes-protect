//! Colour-temperature maths used by the night light and the dimmer.

pub const NEUTRAL_KELVIN: i32 = 6500;
pub const MIN_KELVIN: i32 = 1900;
/// Windows rejects gamma ramps that are too dark.
pub const MIN_BRIGHTNESS: f64 = 0.30;

/// Approximate black-body colour as RGB multipliers in 0..1 (Tanner Helland).
pub fn kelvin_to_rgb(kelvin: f64) -> (f64, f64, f64) {
    let t = kelvin.clamp(1000.0, 40000.0) / 100.0;
    let (r, g) = if t <= 66.0 {
        (255.0, 99.4708025861 * t.ln() - 161.1195681661)
    } else {
        (
            329.698727446 * (t - 60.0).powf(-0.1332047592),
            288.1221695283 * (t - 60.0).powf(-0.0755148492),
        )
    };
    let b = if t >= 66.0 {
        255.0
    } else if t <= 19.0 {
        0.0
    } else {
        138.5177312231 * (t - 10.0).ln() - 305.0447927307
    };
    let clamp = |v: f64| v.clamp(0.0, 255.0) / 255.0;
    (clamp(r), clamp(g), clamp(b))
}

/// Map a 0..100 warmth slider onto 6500K (off) .. 1900K (very warm).
pub fn strength_to_kelvin(strength: i32) -> i32 {
    let s = f64::from(strength.clamp(0, 100));
    (f64::from(NEUTRAL_KELVIN) - f64::from(NEUTRAL_KELVIN - MIN_KELVIN) * s / 100.0)
        .round_ties_even() as i32
}

pub fn kelvin_to_strength(kelvin: i32) -> i32 {
    let span = f64::from(NEUTRAL_KELVIN - MIN_KELVIN);
    let v = (f64::from(NEUTRAL_KELVIN - kelvin) * 100.0 / span).round_ties_even() as i32;
    v.clamp(0, 100)
}

/// Combine warmth and brightness (0..1) into per-channel gamma multipliers.
pub fn channel_multipliers(kelvin: f64, brightness: f64) -> (f64, f64, f64) {
    let brightness = brightness.clamp(MIN_BRIGHTNESS, 1.0);
    let (r, g, b) = kelvin_to_rgb(kelvin);
    let (nr, ng, nb) = kelvin_to_rgb(f64::from(NEUTRAL_KELVIN));
    ((r / nr).min(1.0) * brightness, (g / ng).min(1.0) * brightness, (b / nb).min(1.0) * brightness)
}

/// A 3x256 16-bit gamma ramp (the layout `SetDeviceGammaRamp` expects).
pub type Ramp = [[u16; 256]; 3];

pub fn build_ramp(multipliers: (f64, f64, f64)) -> Ramp {
    let mut ramp = [[0u16; 256]; 3];
    for (channel, m) in [multipliers.0, multipliers.1, multipliers.2].into_iter().enumerate() {
        for (i, slot) in ramp[channel].iter_mut().enumerate() {
            *slot = ((i as f64 * 257.0 * m).round_ties_even() as i64).clamp(0, 65535) as u16;
        }
    }
    ramp
}

/// The no-op ramp (what Windows has when no colour correction is active).
pub fn identity_ramp() -> Ramp {
    build_ramp((1.0, 1.0, 1.0))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn identity_ramp_is_linear() {
        let ramp = identity_ramp();
        assert!(ramp.iter().all(|c| c[0] == 0 && c[255] == 65535 && c[128] == 128 * 257));
    }

    #[test]
    fn neutral_is_identity() {
        let (r, g, b) = channel_multipliers(f64::from(NEUTRAL_KELVIN), 1.0);
        for v in [r, g, b] {
            assert!((v - 1.0).abs() < 1e-3, "{v}");
        }
    }

    #[test]
    fn warm_reduces_blue_most() {
        let (r, g, b) = channel_multipliers(3000.0, 1.0);
        assert!(r >= g && g > b);
    }

    #[test]
    fn brightness_is_clamped() {
        let (r, _, _) = channel_multipliers(f64::from(NEUTRAL_KELVIN), 0.0);
        assert!(r >= 0.3 - 1e-9);
    }

    #[test]
    fn strength_mapping_roundtrip() {
        assert_eq!(strength_to_kelvin(0), NEUTRAL_KELVIN);
        assert_eq!(strength_to_kelvin(100), 1900);
        for s in [0, 25, 50, 75, 100] {
            assert_eq!(kelvin_to_strength(strength_to_kelvin(s)), s);
        }
    }

    #[test]
    fn strength_is_clamped() {
        assert_eq!(strength_to_kelvin(-10), NEUTRAL_KELVIN);
        assert_eq!(strength_to_kelvin(500), 1900);
        assert_eq!(kelvin_to_strength(20000), 0);
        assert_eq!(kelvin_to_strength(100), 100);
    }

    #[test]
    fn ramp_shape_and_monotonic() {
        let ramp = build_ramp((1.0, 0.8, 0.5));
        assert_eq!(ramp[0][255], 65535);
        assert!(ramp[2][255] < ramp[1][255] && ramp[1][255] < ramp[0][255]);
        assert!(ramp[1].windows(2).all(|w| w[0] <= w[1]));
    }
}
