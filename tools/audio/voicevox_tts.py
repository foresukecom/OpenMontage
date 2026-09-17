"""VOICEVOX local Japanese text-to-speech provider tool.

VOICEVOX ENGINE is a free, offline Japanese speech synthesizer that exposes an
HTTP API (default http://127.0.0.1:50021).  Synthesis is a two-step call:
``/audio_query`` builds an editable prosody query, ``/synthesis`` renders it to
WAV.  Prosody controls (speed, pitch, intonation) are fields on that query, not
request parameters, which is why the tool always goes through both steps.

The engine is a long-running server.  When it is installed but not listening,
``execute()`` starts it once and reuses it for the rest of the session -- the
first call pays the model-load cost, later calls do not.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from pathlib import Path
from typing import Any, Optional

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)

DEFAULT_URL = "http://127.0.0.1:50021"
DEFAULT_ENGINE_DIR = "/opt/voicevox/engine"

# Speaker ids are stable across engine releases. These are the common presets;
# the full catalogue comes from the `list_speakers` operation at runtime.
VOICE_ALIASES = {
    "zundamon": 3,
    "ずんだもん": 3,
    "metan": 2,
    "四国めたん": 2,
    "tsumugi": 8,
    "春日部つむぎ": 8,
    "ritsu": 9,
    "波音リツ": 9,
    "hau": 10,
    "雨晴はう": 10,
    "takehiro": 11,
    "玄野武宏": 11,
    "kotaro": 12,
    "白上虎太郎": 12,
    "ryusei": 13,
    "青山龍星": 13,
}


class VoicevoxTTS(BaseTool):
    name = "voicevox_tts"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "voicevox"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL

    dependencies = ["service:voicevox_engine"]
    install_instructions = (
        "Install VOICEVOX ENGINE (free, offline Japanese TTS):\n"
        "  1. Download the build for your platform from\n"
        "     https://github.com/VOICEVOX/voicevox_engine/releases\n"
        "     (linux-cpu-arm64 / linux-cpu-x64 / macos-arm64 / windows-cpu)\n"
        "  2. Extract it and point VOICEVOX_ENGINE_PATH at the 'run' binary,\n"
        f"     or install it at {DEFAULT_ENGINE_DIR}/run\n"
        "  3. The tool starts the engine on first use. To run it yourself:\n"
        "       ./run --host 127.0.0.1 --port 50021\n"
        "Already running elsewhere? Set VOICEVOX_URL to its base URL.\n"
        "Licensing: free for commercial and non-commercial use, but a credit\n"
        "such as 'VOICEVOX:<character>' is REQUIRED, and each voice library\n"
        "carries its own terms -- see https://voicevox.hiroshiba.jp/term/"
    )
    agent_skills = ["text-to-speech"]

    capabilities = [
        "text_to_speech",
        "offline_generation",
        "japanese_narration",
        "prosody_control",
    ]
    supports = {
        "voice_cloning": False,
        "multilingual": False,
        "offline": True,
        "native_audio": True,
        "japanese": True,
        "word_timestamps": False,
    }
    best_for = [
        "Japanese narration without an API key or per-character cost",
        "character-voiced explainers, VTuber-style and anime-style delivery",
        "privacy-sensitive Japanese workflows that must stay on the machine",
    ]
    not_good_for = [
        "any language other than Japanese",
        "neutral corporate or documentary narration (voices are characterful)",
        "voice clone matching",
    ]

    input_schema = {
        "type": "object",
        "required": [],
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["synthesize", "list_speakers"],
                "default": "synthesize",
                "description": "'list_speakers' returns the engine's voice catalogue without generating audio.",
            },
            "text": {
                "type": "string",
                "description": "Japanese text to speak. Required for 'synthesize'.",
            },
            "speaker": {
                "type": "integer",
                "description": "VOICEVOX speaker (style) id. Default 3 = ずんだもん ノーマル.",
                "default": 3,
            },
            "voice": {
                "type": "string",
                "description": (
                    "Character name instead of a numeric id "
                    "(e.g. 'ずんだもん', 'zundamon', '四国めたん'). Overrides 'speaker'."
                ),
            },
            "speed_scale": {
                "type": "number",
                "default": 1.0,
                "description": "Speaking rate. 1.0 = normal, 1.2 = 20% faster.",
            },
            "pitch_scale": {
                "type": "number",
                "default": 0.0,
                "description": "Pitch shift, roughly -0.15..0.15. 0.0 = unchanged.",
            },
            "intonation_scale": {
                "type": "number",
                "default": 1.0,
                "description": "Intonation range. 0.0 = flat, >1.0 = more expressive.",
            },
            "volume_scale": {"type": "number", "default": 1.0},
            "pre_phoneme_length": {
                "type": "number",
                "default": 0.1,
                "description": "Silence before speech, in seconds.",
            },
            "post_phoneme_length": {
                "type": "number",
                "default": 0.1,
                "description": "Silence after speech, in seconds.",
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=2, ram_mb=2048, vram_mb=0, disk_mb=2600, network_required=False
    )
    retry_policy = RetryPolicy(max_retries=1, retryable_errors=[])
    idempotency_key_fields = ["text", "speaker", "voice", "speed_scale", "pitch_scale"]
    side_effects = [
        "writes audio file to output_path",
        "starts a local VOICEVOX ENGINE server process when one is not already listening",
    ]
    user_visible_verification = [
        "Listen to the generated audio for correct Japanese reading of names and numbers",
        "Confirm the credit 'VOICEVOX:<character>' is carried into the final video",
    ]

    # Probing the engine is a socket round-trip; the registry asks for status
    # many times per run, so the answer is cached per process.
    _status_cache: Optional[ToolStatus] = None

    # ---- Engine location ----

    @staticmethod
    def _base_url() -> str:
        return os.environ.get("VOICEVOX_URL", DEFAULT_URL).rstrip("/")

    @classmethod
    def _engine_binary(cls) -> Optional[Path]:
        configured = os.environ.get("VOICEVOX_ENGINE_PATH")
        candidates = [Path(configured)] if configured else []
        candidates.append(Path(DEFAULT_ENGINE_DIR) / "run")
        for path in candidates:
            if path.is_file() and os.access(path, os.X_OK):
                return path
        return None

    @classmethod
    def _server_listening(cls, timeout: float = 0.5) -> bool:
        parsed = urllib.parse.urlparse(cls._base_url())
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    # ---- Status ----

    def get_status(self) -> ToolStatus:
        if VoicevoxTTS._status_cache is not None:
            return VoicevoxTTS._status_cache

        # Either a running engine or an installed one we can start counts as
        # available -- execute() bridges the gap by launching it.
        if self._server_listening() or self._engine_binary() is not None:
            status = ToolStatus.AVAILABLE
        else:
            status = ToolStatus.UNAVAILABLE

        VoicevoxTTS._status_cache = status
        return status

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def estimate_runtime(self, inputs: dict[str, Any]) -> float:
        # Roughly real-time on CPU, plus engine start on the first call.
        chars = len(str(inputs.get("text", "")))
        return max(2.0, chars / 12.0)

    # ---- Engine lifecycle ----

    def _ensure_engine(self, startup_timeout: float = 120.0) -> None:
        """Make sure an engine is listening, starting the bundled one if needed."""
        if self._server_listening():
            return

        binary = self._engine_binary()
        if binary is None:
            raise RuntimeError(
                f"No VOICEVOX ENGINE listening at {self._base_url()} and no engine "
                f"binary found. {self.install_instructions}"
            )

        parsed = urllib.parse.urlparse(self._base_url())
        # Detached so the engine outlives this tool call and serves later ones.
        subprocess.Popen(
            [
                str(binary),
                "--host", parsed.hostname or "127.0.0.1",
                "--port", str(parsed.port or 50021),
            ],
            cwd=str(binary.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        deadline = time.time() + startup_timeout
        while time.time() < deadline:
            if self._server_listening(timeout=1.0):
                return
            time.sleep(1.0)

        raise RuntimeError(
            f"VOICEVOX ENGINE did not become ready within {startup_timeout:.0f}s. "
            f"Start it manually with: {binary} --host 127.0.0.1 --port 50021"
        )

    # ---- HTTP helpers ----

    def _request(
        self,
        path: str,
        *,
        method: str = "GET",
        params: Optional[dict[str, Any]] = None,
        body: Optional[bytes] = None,
        timeout: float = 180.0,
    ) -> bytes:
        url = f"{self._base_url()}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        headers = {"Content-Type": "application/json"} if body is not None else {}
        # /audio_query takes its text as a query parameter but is still a POST;
        # sending GET there returns 405.
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            raise RuntimeError(f"VOICEVOX {path} failed ({exc.code}): {detail}") from exc

    def _resolve_speaker(self, inputs: dict[str, Any]) -> int:
        voice = inputs.get("voice") or inputs.get("voice_id")
        if voice is not None:
            # A numeric string in 'voice' is a speaker id from the selector.
            text_value = str(voice).strip()
            if text_value.isdigit():
                return int(text_value)
            alias = VOICE_ALIASES.get(text_value) or VOICE_ALIASES.get(text_value.lower())
            if alias is not None:
                return alias
            raise ValueError(
                f"Unknown VOICEVOX voice {voice!r}. Use a speaker id, one of "
                f"{sorted(k for k in VOICE_ALIASES if k.isascii())}, or call "
                "operation='list_speakers' for the full catalogue."
            )
        return int(inputs.get("speaker", 3))

    # ---- Execution ----

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        start = time.time()
        operation = inputs.get("operation", "synthesize")

        try:
            self._ensure_engine()
            if operation == "list_speakers":
                result = self._list_speakers()
            else:
                result = self._synthesize(inputs)
        except Exception as exc:
            return ToolResult(success=False, error=f"VOICEVOX TTS failed: {exc}")

        result.duration_seconds = round(time.time() - start, 2)
        return result

    def _list_speakers(self) -> ToolResult:
        speakers = json.loads(self._request("/speakers", timeout=30.0))
        catalogue = [
            {
                "name": speaker.get("name"),
                "styles": [
                    {"id": style.get("id"), "name": style.get("name")}
                    for style in speaker.get("styles", [])
                ],
            }
            for speaker in speakers
        ]
        return ToolResult(
            success=True,
            data={
                "provider": self.provider,
                "speaker_count": len(catalogue),
                "style_count": sum(len(s["styles"]) for s in catalogue),
                "speakers": catalogue,
            },
        )

    def _synthesize(self, inputs: dict[str, Any]) -> ToolResult:
        text = inputs.get("text")
        if not text:
            raise ValueError("'text' is required for operation='synthesize'")

        speaker = self._resolve_speaker(inputs)
        output_path = Path(inputs.get("output_path", "voicevox_output.wav"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Step 1: build the prosody query the engine will render.
        query = json.loads(
            self._request(
                "/audio_query", method="POST", params={"text": text, "speaker": speaker}
            )
        )

        # Step 2: apply prosody controls. The selector speaks in 'speed'/
        # 'speaking_rate'; VOICEVOX calls the same thing speedScale.
        speed = inputs.get("speed_scale", inputs.get("speaking_rate", inputs.get("speed")))
        query["speedScale"] = float(speed) if speed is not None else 1.0
        query["pitchScale"] = float(inputs.get("pitch_scale", 0.0))
        query["intonationScale"] = float(inputs.get("intonation_scale", 1.0))
        query["volumeScale"] = float(inputs.get("volume_scale", 1.0))
        query["prePhonemeLength"] = float(inputs.get("pre_phoneme_length", 0.1))
        query["postPhonemeLength"] = float(inputs.get("post_phoneme_length", 0.1))

        # Step 3: render to WAV.
        audio = self._request(
            "/synthesis",
            method="POST",
            params={"speaker": speaker},
            body=json.dumps(query).encode("utf-8"),
        )
        output_path.write_bytes(audio)

        with wave.open(str(output_path), "rb") as handle:
            audio_seconds = round(handle.getnframes() / float(handle.getframerate()), 2)
            sample_rate = handle.getframerate()

        return ToolResult(
            success=True,
            model=f"voicevox-speaker-{speaker}",
            data={
                "provider": self.provider,
                "speaker": speaker,
                "text_length": len(text),
                "audio_seconds": audio_seconds,
                "sample_rate": sample_rate,
                "speed_scale": query["speedScale"],
                "output": str(output_path),
                "format": "wav",
                "attribution_required": f"VOICEVOX:speaker-{speaker}",
            },
            artifacts=[str(output_path)],
        )
