//! Soft synthesized chimes (no bundled audio files).
//!
//! The WAV is generated in memory, cached under the config folder and handed to a
//! platform-specific player (see `platform::play_sound_file` on Windows).

use std::f64::consts::PI;
use std::path::{Path, PathBuf};

use super::config::config_dir;

pub const RATE: u32 = 44_100;
pub const KINDS: [&str; 3] = ["start", "end", "notify"];
/// Leave headroom: never full scale.
const PEAK: f64 = 0.55;

/// `(frequency Hz, start offset s, length s)` for every note of each chime.
fn notes(kind: &str) -> Option<&'static [(f64, f64, f64)]> {
    Some(match kind {
        "start" => &[(523.25, 0.00, 0.60), (659.25, 0.18, 0.70)],
        "end" => &[(659.25, 0.00, 0.55), (523.25, 0.20, 0.55), (392.00, 0.40, 0.80)],
        "notify" => &[(783.99, 0.00, 0.50)],
        _ => return None,
    })
}

fn tone(freq: f64, length: f64, gain: f64) -> Vec<f64> {
    let n = (f64::from(RATE) * length) as usize;
    (0..n)
        .map(|i| {
            let t = i as f64 / f64::from(RATE);
            let attack = (t / 0.012).min(1.0); // 12 ms fade-in avoids a click
            let decay = (-5.0 * t / length).exp(); // bell-like fade-out
            let wave = (2.0 * PI * freq * t).sin() + 0.25 * (2.0 * PI * 2.0 * freq * t).sin();
            wave * attack * decay * gain
        })
        .collect()
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UnknownSound(pub String);
impl std::fmt::Display for UnknownSound {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "unknown sound: {}", self.0)
    }
}
impl std::error::Error for UnknownSound {}

/// A mono 16-bit WAV for `kind` at volume 0..=100.
pub fn synth(kind: &str, volume: i32) -> Result<Vec<u8>, UnknownSound> {
    let notes = notes(kind).ok_or_else(|| UnknownSound(kind.to_string()))?;
    let volume = f64::from(volume.clamp(0, 100));
    let total = notes.iter().map(|(_, start, len)| start + len).fold(0.0, f64::max);
    let mut mix = vec![0.0f64; (f64::from(RATE) * total) as usize];
    let gain = 1.0 / (notes.len() as f64).sqrt();
    for (freq, start, length) in notes {
        let offset = (f64::from(RATE) * start) as usize;
        for (i, v) in tone(*freq, *length, gain).into_iter().enumerate() {
            if let Some(slot) = mix.get_mut(offset + i) {
                *slot += v;
            }
        }
    }
    let peak = mix.iter().fold(1e-9f64, |m, v| m.max(v.abs()));
    let scale = PEAK * (volume / 100.0) / peak;
    let samples: Vec<i16> = mix.iter().map(|v| ((v * scale).clamp(-1.0, 1.0) * 32767.0) as i16).collect();
    Ok(wav_bytes(&samples))
}

fn wav_bytes(samples: &[i16]) -> Vec<u8> {
    let data_len = (samples.len() * 2) as u32;
    let mut out = Vec::with_capacity(44 + samples.len() * 2);
    out.extend_from_slice(b"RIFF");
    out.extend_from_slice(&(36 + data_len).to_le_bytes());
    out.extend_from_slice(b"WAVEfmt ");
    out.extend_from_slice(&16u32.to_le_bytes()); // PCM header size
    out.extend_from_slice(&1u16.to_le_bytes()); // PCM
    out.extend_from_slice(&1u16.to_le_bytes()); // mono
    out.extend_from_slice(&RATE.to_le_bytes());
    out.extend_from_slice(&(RATE * 2).to_le_bytes()); // byte rate
    out.extend_from_slice(&2u16.to_le_bytes()); // block align
    out.extend_from_slice(&16u16.to_le_bytes()); // bits per sample
    out.extend_from_slice(b"data");
    out.extend_from_slice(&data_len.to_le_bytes());
    for s in samples {
        out.extend_from_slice(&s.to_le_bytes());
    }
    out
}

pub struct SoundPlayer {
    pub cache_dir: PathBuf,
}

impl SoundPlayer {
    pub fn new() -> Self {
        Self { cache_dir: config_dir().join("sounds") }
    }

    pub fn with_cache_dir(cache_dir: PathBuf) -> Self {
        Self { cache_dir }
    }

    /// Cached file for `kind`; volumes are rounded to steps of 10 (at most 11 files per sound).
    pub fn path_for(&self, kind: &str, volume: i32) -> std::io::Result<PathBuf> {
        let step = ((f64::from(volume) / 10.0).round_ties_even() as i32 * 10).clamp(0, 100);
        let path = self.cache_dir.join(format!("{kind}-{step}.wav"));
        if !path.exists() {
            let bytes = synth(kind, step).map_err(std::io::Error::other)?;
            std::fs::create_dir_all(&self.cache_dir)?;
            std::fs::write(&path, bytes)?;
        }
        Ok(path)
    }

    /// Play through `player` (the platform backend). Returns whether a sound was started.
    pub fn play(&self, kind: &str, volume: i32, player: &dyn Fn(&Path) -> bool) -> bool {
        if volume <= 0 || notes(kind).is_none() {
            return false;
        }
        match self.path_for(kind, volume) {
            Ok(path) => player(&path),
            Err(_) => false,
        }
    }
}

impl Default for SoundPlayer {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;

    /// `(channels, width, rate, frames, samples)` from a canonical 44-byte-header WAV.
    fn read(data: &[u8]) -> (u16, u16, u32, usize, Vec<i16>) {
        assert_eq!(&data[0..4], b"RIFF");
        assert_eq!(&data[8..16], b"WAVEfmt ");
        let u16_at = |i: usize| u16::from_le_bytes([data[i], data[i + 1]]);
        let u32_at = |i: usize| u32::from_le_bytes([data[i], data[i + 1], data[i + 2], data[i + 3]]);
        assert_eq!(u32_at(4) as usize, data.len() - 8);
        let samples: Vec<i16> = data[44..].chunks(2).map(|c| i16::from_le_bytes([c[0], c[1]])).collect();
        (u16_at(22), u16_at(34) / 8, u32_at(24), samples.len(), samples)
    }
    fn peak(s: &[i16]) -> i32 {
        s.iter().map(|v| i32::from(*v).abs()).max().unwrap_or(0)
    }

    #[test]
    fn valid_mono_16bit_wav_with_sane_length() {
        for kind in KINDS {
            let (ch, width, rate, n, _) = read(&synth(kind, 50).unwrap());
            assert_eq!((ch, width, rate), (1, 2, RATE));
            let secs = n as f64 / f64::from(rate);
            assert!(0.4 < secs && secs < 1.5, "{kind} {secs}");
        }
    }

    #[test]
    fn volume_scales_peak_and_never_clips() {
        let p = |v| peak(&read(&synth("start", v).unwrap()).4);
        let (quiet, loud) = (p(20), p(100));
        assert!(0 < quiet && quiet < loud && f64::from(loud) < 32767.0 * 0.6);
        assert_eq!(p(0), 0);
        assert_eq!(p(999), loud);
    }

    #[test]
    fn each_sound_is_different_and_unknown_rejected() {
        let blobs: std::collections::HashSet<_> = KINDS.iter().map(|k| synth(k, 50).unwrap()).collect();
        assert_eq!(blobs.len(), 3);
        assert!(synth("boing", 50).is_err());
    }

    #[test]
    fn sound_starts_and_ends_quiet_no_click() {
        let s = read(&synth("end", 100).unwrap()).4;
        assert!(i32::from(s[0]).abs() < 200 && i32::from(*s.last().unwrap()).abs() < 800);
    }

    #[test]
    fn player_caches_by_volume_step_and_plays() {
        let dir = tempfile::tempdir().unwrap();
        let played = RefCell::new(Vec::new());
        let backend = |p: &Path| {
            played.borrow_mut().push(p.to_path_buf());
            true
        };
        let sp = SoundPlayer::with_cache_dir(dir.path().to_path_buf());
        assert!(sp.play("start", 52, &backend));
        let first = played.borrow()[0].clone();
        assert_eq!(first.file_name().unwrap(), "start-50.wav");
        assert!(first.exists());
        let mtime = std::fs::metadata(&first).unwrap().modified().unwrap();
        sp.play("start", 48, &backend);
        let second = played.borrow()[1].clone();
        assert_eq!(second, first);
        assert_eq!(std::fs::metadata(&second).unwrap().modified().unwrap(), mtime); // reused, not rewritten
    }

    #[test]
    fn player_ignores_zero_volume_and_unknown_kind() {
        let dir = tempfile::tempdir().unwrap();
        let played = RefCell::new(0);
        let backend = |_: &Path| {
            *played.borrow_mut() += 1;
            true
        };
        let sp = SoundPlayer::with_cache_dir(dir.path().to_path_buf());
        assert!(!sp.play("start", 0, &backend) && !sp.play("nope", 50, &backend));
        assert_eq!(*played.borrow(), 0);
    }
}
