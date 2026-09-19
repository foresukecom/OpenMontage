---
name: voicevox
description: Generate Japanese narration with VOICEVOX ENGINE — a free, offline, character-voiced TTS served over a local HTTP API. Use when a video needs Japanese speech. This is the only available Japanese voice when no cloud TTS key is configured; piper_tts is English-only. Credit such as "VOICEVOX:<character>" is REQUIRED in any output that uses it.
license: MIT (this skill). VOICEVOX ENGINE and its voice libraries carry their own terms — see Licensing below.
compatibility: Runs fully offline. Requires the VOICEVOX ENGINE binary (linux-cpu-arm64 / linux-cpu-x64 / macos-arm64 / windows-cpu) on the machine. No API key, no network.
metadata: {"openclaw": {"requires": {"env": []}}}
---

# VOICEVOX — offline Japanese text-to-speech

Generate Japanese narration with **VOICEVOX ENGINE**, a free Japanese speech
synthesizer that runs as a local HTTP server. In OpenMontage it is exposed
through the `voicevox_tts` tool (`capability=tts`, `provider=voicevox`).

**Why this tool exists:** `piper_tts`, the default offline provider, has **no
Japanese voice model** — its catalogue is English-only. Every other TTS provider
in the registry needs an API key. So when a Japanese video must be produced on a
machine with no keys, VOICEVOX is not merely the cheapest option, it is the only
one.

> Docs: [voicevox_engine](https://github.com/VOICEVOX/voicevox_engine) · [利用規約](https://voicevox.hiroshiba.jp/term/)

## Licensing — read this before shipping anything

VOICEVOX is **free for commercial and non-commercial use**, with two binding
conditions:

1. **A credit is mandatory.** The terms require a credit that makes clear
   VOICEVOX was used. The conventional form is `VOICEVOX:<character>`, e.g.
   `VOICEVOX:ずんだもん`. Put it in the video (an end card works well) or in the
   description — but put it somewhere.
2. **Each voice library has its own terms.** The engine's licence is not the
   character's licence. Check the terms for the specific character you use;
   some restrict certain content or require additional notice.

`voicevox_tts` returns `data.attribution_required` on every successful call and
lists the credit in `user_visible_verification`. **Carry it through to the
`asset_manifest` (`license` field) and into the composition.** A video that
drops the credit is a licence violation, not a cosmetic miss.

## Setup

Download the build for the platform from
[releases](https://github.com/VOICEVOX/voicevox_engine/releases) and extract it.
The CPU builds are ~2.1 GB extracted — budget the disk.

```bash
# The tool looks here by default:
/opt/voicevox/engine/run
# ...or wherever VOICEVOX_ENGINE_PATH points:
export VOICEVOX_ENGINE_PATH=/path/to/run
# If an engine is already running elsewhere:
export VOICEVOX_URL=http://127.0.0.1:50021
```

`voicevox_tts` reports `AVAILABLE` when either the server answers on
`VOICEVOX_URL` **or** an engine binary is present — `execute()` starts the
engine itself on first use and reuses it afterwards.

**The first call pays the model load**, roughly 20–40 s on CPU. Later calls are
near real-time. When generating a batch, expect the first section to be slow and
do not mistake it for a hang.

## The API has one shape that trips agents

Synthesis is **two calls**, and the prosody controls live on the *query object*,
not on the request:

```
POST /audio_query?text=<text>&speaker=<id>   → prosody query JSON
POST /synthesis?speaker=<id>  (body: that JSON, edited)  → WAV bytes
```

Two things reliably go wrong:

- **`/audio_query` takes its text as a query parameter but is still a POST.**
  Sending GET returns `405 Method Not Allowed`.
- **Speed, pitch and intonation are fields you edit on the returned query**
  (`speedScale`, `pitchScale`, `intonationScale`, `volumeScale`,
  `prePhonemeLength`, `postPhonemeLength`). There are no request parameters for
  them, which is why the tool always goes through both steps.

`voicevox_tts` handles all of this. Only reach for raw HTTP when debugging it.

## Using it in a pipeline

Route through `tts_selector` as usual — it auto-discovers VOICEVOX from the
registry. To pin it:

```python
{"preferred_provider": "voicevox", "text": "...", "output_path": "..."}
```

Or call the tool directly:

```python
{
  "text": "アクセスパターンを先に書き出すのだ。",
  "speaker": 3,               # ずんだもん ノーマル
  "speed_scale": 1.0,
  "intonation_scale": 1.1,    # >1.0 adds warmth; flat reads sound robotic
  "pre_phoneme_length": 0.1,
  "post_phoneme_length": 0.6, # map the script's pause_after_seconds here
  "output_path": "projects/<id>/assets/audio/narration_s1.wav"
}
```

`operation: "list_speakers"` returns the full catalogue without generating audio.

## Voice selection

43 characters / 127 styles ship with the engine. Common ids:

| id | Character | Feel |
|---|---|---|
| 3 | ずんだもん（ノーマル） | Friendly, approachable. The default, and a genre convention in Japanese tech explainers |
| 2 | 四国めたん（ノーマル） | Bright, slightly formal |
| 13 | 青山龍星（ノーマル） | Low, calm — closest to neutral corporate narration |
| 8 | 春日部つむぎ | Youthful, energetic |
| 9 | 波音リツ | Cool, flat affect |

The tool also accepts names: `{"voice": "ずんだもん"}` or `{"voice": "zundamon"}`.
Call `list_speakers` for the rest — ids are stable across engine releases.

**Every voice is characterful.** None of them read as a neutral documentary
narrator. If the brief needs corporate neutrality, say so at proposal time and
offer a cloud provider as the alternative rather than discovering the mismatch
after batch generation.

## Writing the script for it

- **Spell out English in katakana in the narration text.** VOICEVOX reads
  Latin letters unreliably: write `エスキューエル` for SQL, `ダイナモディービー`
  for DynamoDB. Keep the correct spelling for **subtitles** — put the mapping in
  the script's `pronunciation_guides` and reverse it when building captions, so
  viewers read `SQL` while the voice says it properly.
- **Measure, don't estimate, the pace.** Japanese has no word-count analogue to
  the English wpm tables. Generate one representative sentence and divide
  characters by the resulting duration. On `speaker=3` at `speed_scale=1.0`
  this lands around **6.4 characters/second (~386/min)**, but verify per voice —
  and rebuild the timeline from the measured durations, not the estimate.
- **Match the character's register.** A ずんだもん script conventionally ends
  sentences with 〜のだ / 〜なのだ. It is an established style in Japanese tech
  explainers, but it does cost some authority — worth raising with the user when
  the piece is training material.

## Cost

Free. `estimate_cost()` returns `0.0` for every input. There is no quota and no
network call, so batch freely — the only budget is CPU time.

## Limits & tips

- **Japanese only.** No English voice exists. Do not route non-Japanese text here.
- Output is **24 kHz mono WAV**. Mix with `audio_mixer` before composition.
- The engine is a long-running server. It survives between tool calls; you do
  not need to restart it per section.
- `voicevox_tts` sets `supports.multilingual = False` deliberately — the
  selector's ranking should never pick it for a non-Japanese brief.
