import io
import wave

import pytest

from eyecare.core import sounds, winapi


def read(data):
    with wave.open(io.BytesIO(data)) as w:
        frames = w.readframes(w.getnframes())
        return w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes(), frames


def peak(frames):
    import struct

    return max(abs(v) for (v,) in struct.iter_unpack("<h", frames))


def test_valid_mono_16bit_wav_with_sane_length():
    for kind in sounds.KINDS:
        ch, width, rate, n, _ = read(sounds.synth(kind, 50))
        assert (ch, width, rate) == (1, 2, sounds.RATE)
        assert 0.4 < n / rate < 1.5


def test_volume_scales_peak_and_never_clips():
    quiet = peak(read(sounds.synth("start", 20))[4])
    loud = peak(read(sounds.synth("start", 100))[4])
    assert 0 < quiet < loud < 32767 * 0.6
    assert peak(read(sounds.synth("start", 0))[4]) == 0
    assert peak(read(sounds.synth("start", 999))[4]) == peak(read(sounds.synth("start", 100))[4])


def test_each_sound_is_different_and_unknown_rejected():
    blobs = {k: sounds.synth(k, 50) for k in sounds.KINDS}
    assert len(set(blobs.values())) == 3
    with pytest.raises(ValueError):
        sounds.synth("boing", 50)


def test_sound_starts_and_ends_silent_no_click():
    frames = read(sounds.synth("end", 100))[4]
    import struct

    first = struct.unpack("<h", frames[:2])[0]
    last = struct.unpack("<h", frames[-2:])[0]
    assert abs(first) < 200 and abs(last) < 800


def test_player_caches_by_volume_step_and_plays(tmp_path, monkeypatch):
    played = []
    monkeypatch.setattr(winapi, "play_sound_file", lambda p: played.append(p) or True)
    sp = sounds.SoundPlayer(tmp_path)
    assert sp.play("start", 52) is True
    assert played[0].name == "start-50.wav" and played[0].exists()
    mtime = played[0].stat().st_mtime_ns
    sp.play("start", 48)
    assert played[1] == played[0] and played[1].stat().st_mtime_ns == mtime  # reused, not rewritten


def test_player_ignores_zero_volume_and_unknown_kind(tmp_path, monkeypatch):
    played = []
    monkeypatch.setattr(winapi, "play_sound_file", lambda p: played.append(p) or True)
    sp = sounds.SoundPlayer(tmp_path)
    assert sp.play("start", 0) is False and sp.play("nope", 50) is False and played == []


def test_play_is_noop_off_windows():
    if not winapi.IS_WINDOWS:
        assert winapi.play_sound_file("x.wav") is False
