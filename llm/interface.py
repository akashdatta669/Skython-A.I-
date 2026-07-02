"""
llm/interface.py — Abstract base class for all LLM backends
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generator


class LLMInterface(ABC):
    """Model-agnostic interface. All adapters must implement this contract."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
    ) -> str:
        """Synchronous generation. Returns the full response as a string."""
        ...

    @abstractmethod
    def stream(
        self,
        prompt: str,
        system_prompt: str = "",
    ) -> Generator[str, None, None]:
        """Streaming generation. Yields string tokens one by one."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the LLM backend is online and reachable."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the active model identifier string."""
        ...
