"""Unit tests for the VOICEVOX phoneme timeline (tools/audio/voicevox_tts.py).

The engine is never called. The timeline must reproduce how VOICEVOX renders a
query — per-phoneme rounding to 24000/256 Hz frames after speedScale, plus the
rising vowel /synthesis appends to interrogative phrases — because lip sync is
driven from it. Against a live engine 0.25.2 this model matched WAV length to
the sample on every sentence tried.
"""

from __future__ import annotations

from tools.audio.voicevox_tts import VoicevoxTTS

FRAME = 256 / 24000


def _mora(text, vowel, vowel_length, consonant=None, consonant_length=None, pitch=5.5):
    return {
        "text": text,
        "consonant": consonant,
        "consonant_length": consonant_length,
        "vowel": vowel,
        "vowel_length": vowel_length,
        "pitch": pitch,
    }


def _query(phrases, speed=1.0):
    return {
        "accent_phrases": phrases,
        "speedScale": speed,
        "prePhonemeLength": 0.1,
        "postPhonemeLength": 0.1,
    }


def _frames(seconds):
    return round(seconds / FRAME)


def test_phonemes_are_contiguous_and_frame_aligned():
    query = _query([
        {"moras": [_mora("ノ", "o", 0.0977, "n", 0.0600), _mora("ダ", "a", 0.2119, "d", 0.0507)],
         "pause_mora": None},
    ])
    phonemes = VoicevoxTTS._phoneme_timeline(query)

    assert [p["phoneme"] for p in phonemes] == ["pau", "n", "o", "d", "a", "pau"]
    assert phonemes[0]["start"] == 0.0
    for prev, cur in zip(phonemes, phonemes[1:]):
        assert prev["end"] == cur["start"]
    # Each length is rounded to whole frames on its own, not summed then rounded.
    expected = sum(round(x / FRAME) for x in (0.1, 0.0600, 0.0977, 0.0507, 0.2119, 0.1))
    assert _frames(phonemes[-1]["end"]) == expected


def test_speed_scale_shortens_every_phoneme_including_silence():
    query = _query([{"moras": [_mora("ア", "a", 0.3)], "pause_mora": None}], speed=1.5)
    phonemes = VoicevoxTTS._phoneme_timeline(query)

    assert _frames(phonemes[0]["end"]) == round(0.1 / 1.5 / FRAME)
    assert _frames(phonemes[1]["end"] - phonemes[1]["start"]) == round(0.3 / 1.5 / FRAME)


def test_pause_mora_becomes_a_pause_phoneme():
    query = _query([
        {"moras": [_mora("ア", "a", 0.1)], "pause_mora": {"vowel_length": 0.3}},
        {"moras": [_mora("イ", "i", 0.1)], "pause_mora": None},
    ])
    phonemes = VoicevoxTTS._phoneme_timeline(query)

    assert [(p["phoneme"], p["mora"]) for p in phonemes] == [
        ("pau", ""), ("a", "ア"), ("pau", "、"), ("i", "イ"), ("pau", ""),
    ]


def test_interrogative_phrase_gets_upspeak_vowel():
    query = _query([
        {"moras": [_mora("ダ", "a", 0.2, "d", 0.05)], "pause_mora": None, "is_interrogative": True},
    ])
    phonemes = VoicevoxTTS._phoneme_timeline(query)

    upspeak = phonemes[-2]
    assert upspeak["phoneme"] == "a"
    assert _frames(upspeak["end"] - upspeak["start"]) == round(0.15 / FRAME)


def test_unvoiced_interrogative_ending_gets_no_upspeak():
    query = _query([
        {"moras": [_mora("ッ", "cl", 0.06, pitch=0.0)], "pause_mora": None, "is_interrogative": True},
    ])
    phonemes = VoicevoxTTS._phoneme_timeline(query)

    assert [p["phoneme"] for p in phonemes] == ["pau", "cl", "pau"]
