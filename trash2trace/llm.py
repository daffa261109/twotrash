"""Mengirim foto sampah ke LLM yang OpenAI-compatible."""

from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.request

from trash2trace.labels import canonical_class
from trash2trace.settings import LlmConfig, load_llm_config

_PROMPT = (
    "Classify the waste in this photo as exactly one label: "
    "organic, nonorganic, or other. "
    'Reply with JSON only: {"label":"organic","confidence":0.0}'
)


class LlmVision:
    def __init__(self, config: LlmConfig | None = None) -> None:
        self.config = config or load_llm_config()
        print(
            f"[INFO] LLM {self.config.provider} model={self.config.model} "
            f"endpoint={self.config.endpoint}"
        )

    def classify(self, jpeg: bytes) -> tuple[str, float]:
        payload = {
            "model": self.config.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": _data_url(jpeg)},
                        },
                    ],
                }
            ],
        }
        request = urllib.request.Request(
            _chat_url(self.config.endpoint),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"LLM menolak permintaan ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM tidak terjangkau: {exc.reason}") from exc
        return _parse_reply(body)


def _chat_url(endpoint: str) -> str:
    endpoint = endpoint.rstrip("/")
    if endpoint.endswith("/chat/completions"):
        return endpoint
    return endpoint + "/chat/completions"


def _data_url(jpeg: bytes) -> str:
    encoded = base64.b64encode(jpeg).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _parse_reply(body: str) -> tuple[str, float]:
    data = json.loads(body)
    content = data["choices"][0]["message"]["content"]
    if isinstance(content, list):
        text = "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    else:
        text = str(content)
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match is None:
        raise RuntimeError(f"Jawaban LLM bukan JSON: {text[:200]}")
    reply = json.loads(match.group(0))
    label = canonical_class(str(reply.get("label", "other")))
    try:
        confidence = float(reply.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    return label, min(1.0, max(0.0, confidence))
