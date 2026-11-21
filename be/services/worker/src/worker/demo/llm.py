"""Adapter LLM cho bước sinh script (đổi provider chỉ sửa file này, ADR-0005)."""

from __future__ import annotations

import time
from typing import Protocol

import httpx

from worker.demo.errors import DemoError

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class ScriptLLM(Protocol):
    name: str

    def complete(self, system: str, user: str) -> str:
        """Trả chuỗi JSON (một object)."""
        ...


class OpenAIScriptLLM:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout_s: float = 120.0,
        client: httpx.Client | None = None,
        retry_delays_s: tuple[float, ...] = (3.0, 10.0),
    ) -> None:
        self.name = f"openai:{model}"
        self._model = model
        self._key = api_key
        self._client = client or httpx.Client(timeout=timeout_s)
        self._delays = retry_delays_s
        self.tokens_in = 0
        self.tokens_out = 0

    def complete(self, system: str, user: str) -> str:
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self._key}"}
        err = ""
        for attempt in range(len(self._delays) + 1):
            try:
                r = self._client.post(OPENAI_URL, json=body, headers=headers)
            except httpx.HTTPError as ex:
                err = f"lỗi mạng {type(ex).__name__}"
            else:
                if r.status_code == 200:
                    data = r.json()
                    usage = data.get("usage") or {}
                    self.tokens_in += int(usage.get("prompt_tokens", 0))
                    self.tokens_out += int(usage.get("completion_tokens", 0))
                    try:
                        return data["choices"][0]["message"]["content"]
                    except (KeyError, IndexError, TypeError) as ex:
                        raise DemoError("OpenAI trả response không có nội dung") from ex
                err = f"HTTP {r.status_code}: {r.text[:200]}"
                if r.status_code not in (429, 500, 502, 503, 504):
                    raise DemoError(f"OpenAI từ chối: {err}")  # 4xx khác: thử lại vô ích
            if attempt < len(self._delays):
                time.sleep(self._delays[attempt])
        raise DemoError(f"OpenAI lỗi sau {len(self._delays) + 1} lần: {err}")
