"""
llm/ollama_adapter.py — Gemma 3 adapter via Ollama REST API
"""

from __future__ import annotations

import json
import logging
import time
from typing import Generator

import httpx

from config import (
    OLLAMA_BASE_URL,
    OLLAMA_DEFAULT_MODEL,
    OLLAMA_MAX_TOKENS,
    OLLAMA_PREFERRED_MODELS,
    OLLAMA_RETRY_COUNT,
    OLLAMA_RETRY_DELAY,
    OLLAMA_TIMEOUT,
)
from llm.interface import LLMInterface
from llm.prompts import OFFLINE_RESPONSE

log = logging.getLogger(__name__)


class OllamaAdapter(LLMInterface):
    """
    Adapter for Ollama's local REST API.
    Communicates with http://localhost:11434 — no external internet required.
    """

    def __init__(self) -> None:
        self._model: str = OLLAMA_DEFAULT_MODEL
        self._client = httpx.Client(
            base_url=OLLAMA_BASE_URL,
            timeout=OLLAMA_TIMEOUT,
        )
        self._online: bool = False
        self._detect_model()

    # ────────────────────────── Lifecycle ─────────────────────────────────────

    def _detect_model(self) -> None:
        """Auto-detect the best available Ollama model."""
        try:
            resp = self._client.get("/api/tags", timeout=5)
            if resp.status_code != 200:
                log.warning("Ollama /api/tags returned HTTP %d", resp.status_code)
                return

            data = resp.json()
            available: list[str] = [m["name"] for m in data.get("models", [])]
            log.info("Ollama available models: %s", available)

            for preferred in OLLAMA_PREFERRED_MODELS:
                # Exact match or prefix match (e.g. "gemma3:1b" matches "gemma3:1b-instruct-q4")
                for name in available:
                    if name == preferred or name.startswith(preferred):
                        self._model = name
                        self._online = True
                        log.info("✅ Selected Ollama model: %s", self._model)
                        return

            if available:
                self._model = available[0]
                self._online = True
                log.warning(
                    "No preferred model found. Using first available: %s", self._model
                )
            else:
                log.warning(
                    "⚠️ No models found in Ollama. "
                    "Run: ollama pull %s",
                    OLLAMA_DEFAULT_MODEL,
                )

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            log.warning("⚠️ Ollama not reachable: %s", exc)
            log.warning("LLM features will be unavailable. Run: ollama serve")

    # ────────────────────────── Public interface ───────────────────────────────

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """Ping Ollama root endpoint."""
        try:
            resp = self._client.get("/", timeout=3)
            self._online = resp.status_code == 200
        except Exception:
            self._online = False
        return self._online

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = OLLAMA_MAX_TOKENS,
    ) -> str:
        """Blocking call — returns full response string."""
        if not self.is_available():
            return OFFLINE_RESPONSE

        payload: dict = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        if system_prompt:
            payload["system"] = system_prompt

        for attempt in range(1, OLLAMA_RETRY_COUNT + 1):
            try:
                resp = self._client.post(
                    "/api/generate", json=payload, timeout=OLLAMA_TIMEOUT
                )
                resp.raise_for_status()
                return resp.json().get("response", "")
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                log.warning(
                    "Ollama generate attempt %d/%d failed: %s",
                    attempt,
                    OLLAMA_RETRY_COUNT,
                    exc,
                )
                if attempt < OLLAMA_RETRY_COUNT:
                    time.sleep(OLLAMA_RETRY_DELAY)
            except httpx.HTTPStatusError as exc:
                log.error("Ollama HTTP error: %s", exc)
                break

        return OFFLINE_RESPONSE

    def stream(
        self,
        prompt: str,
        system_prompt: str = "",
    ) -> Generator[str, None, None]:
        """Streaming call — yields tokens one by one."""
        if not self.is_available():
            yield OFFLINE_RESPONSE
            return

        payload: dict = {
            "model": self._model,
            "prompt": prompt,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            with self._client.stream(
                "POST", "/api/generate", json=payload, timeout=OLLAMA_TIMEOUT
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            yield token
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            log.error("Ollama stream error: %s", exc)
            yield OFFLINE_RESPONSE

    def list_models(self) -> list[str]:
        """Return all models currently available in Ollama."""
        try:
            resp = self._client.get("/api/tags", timeout=5)
            if resp.status_code == 200:
                return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            pass
        return []

    def close(self) -> None:
        self._client.close()
