import base64
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from adapter import GeminiTTS, LiveCallsDisabledError  # noqa: E402


def _pcm_b64(seconds: float, rate: int = 24000) -> str:
    return base64.b64encode(bytes(int(seconds * rate) * 2)).decode()


class _FakeInteractions:
    def __init__(self, b64: str, usage: object | None = None) -> None:
        self.b64, self.usage, self.last_body = b64, usage, None

    def create(self, **body: object) -> SimpleNamespace:
        self.last_body = body
        return SimpleNamespace(output_audio=SimpleNamespace(data=self.b64), usage=self.usage)


def _client(b64: str, usage: object | None = None) -> tuple[SimpleNamespace, _FakeInteractions]:
    inter = _FakeInteractions(b64, usage)
    return SimpleNamespace(interactions=inter), inter


def test_refuses_live_call_without_flag(tmp_path: Path) -> None:
    with pytest.raises(LiveCallsDisabledError):
        GeminiTTS(tmp_path).synthesize("xin chào", "Kore")


def test_parses_pcm_audio_and_builds_request(tmp_path: Path) -> None:
    client, inter = _client(_pcm_b64(1.5))
    res = GeminiTTS(tmp_path, client=client).synthesize("xin chào", "Kore", speed=1.3)
    assert res.duration_s == pytest.approx(1.5, abs=0.01)
    assert res.provider == "google" and res.cost.unit == "characters" and res.cost.cost_status == "estimated"
    body = inter.last_body
    assert isinstance(body, dict)
    assert body["model"] == "gemini-3.8-flash-tts"
    assert body["generation_config"] == {"speech_config": [{"voice": "Kore"}]}
    style = body["input"][0]["content"][0]["annotations"][0]["style"]  # type: ignore[index]
    assert "speaking rapidly" in style


def test_uses_usage_tokens_when_present(tmp_path: Path) -> None:
    client, _ = _client(_pcm_b64(0.5), usage=SimpleNamespace(total_tokens=321))
    res = GeminiTTS(tmp_path, client=client).synthesize("a", "Kore")
    assert (res.cost.unit, res.cost.quantity, res.cost.cost_status) == ("tokens", 321, "exact")


def test_call_limit_stops_before_quota(tmp_path: Path) -> None:
    client, _ = _client(_pcm_b64(0.2))
    tts = GeminiTTS(tmp_path, client=client, max_calls=2)
    tts.synthesize("a", "Kore")
    tts.synthesize("b", "Kore")
    with pytest.raises(RuntimeError, match="giới hạn"):
        tts.synthesize("c", "Kore")
