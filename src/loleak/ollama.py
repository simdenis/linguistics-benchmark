from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass
class OllamaResponse:
    model: str
    response: str
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None
    total_duration_ns: Optional[int] = None


class OllamaClient:
    """Minimal Ollama HTTP client."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")

    def generate(
        self,
        model: str,
        prompt: str,
        *,
        temperature: float = 0.0,
        top_p: float = 1.0,
        num_ctx: int = 4096,
        seed: Optional[int] = 0,
        extra_options: Optional[Dict[str, Any]] = None,
        timeout_s: int = 600,
    ) -> OllamaResponse:
        url = f"{self.base_url}/api/generate"
        options: Dict[str, Any] = {
            "temperature": temperature,
            "top_p": top_p,
            "num_ctx": num_ctx,
        }
        if seed is not None:
            options["seed"] = seed
        if extra_options:
            options.update(extra_options)

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }

        r = requests.post(url, json=payload, timeout=timeout_s)
        r.raise_for_status()
        data = r.json()
        return OllamaResponse(
            model=data.get("model", model),
            response=data.get("response", ""),
            prompt_eval_count=data.get("prompt_eval_count"),
            eval_count=data.get("eval_count"),
            total_duration_ns=data.get("total_duration"),
        )
