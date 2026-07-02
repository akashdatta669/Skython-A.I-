"""
skills/registry.py — Skill registry pattern
"""

from __future__ import annotations

import logging
from typing import Any, Callable

log = logging.getLogger(__name__)


class Skill:
    """Represents a single teachable skill/strategy."""

    def __init__(self, name: str, description: str, handler: Callable[..., str]) -> None:
        self.name = name
        self.description = description
        self._handler = handler

    def execute(self, **kwargs: Any) -> str:
        return self._handler(**kwargs)

    def __repr__(self) -> str:
        return f"<Skill name={self.name!r}>"


class SkillRegistry:
    """Central registry for all teaching skills."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill
        log.debug("Skill registered: %s", skill.name)

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list_skills(self) -> list[dict[str, str]]:
        return [
            {"name": s.name, "description": s.description}
            for s in self._skills.values()
        ]

    def execute(self, name: str, **kwargs: Any) -> str:
        skill = self.get(name)
        if not skill:
            raise ValueError(f"Unknown skill: {name}")
        return skill.execute(**kwargs)

    def __len__(self) -> int:
        return len(self._skills)


# ─────────────────────────── Global registry ─────────────────────────────────

_global_registry: SkillRegistry | None = None


def get_registry() -> SkillRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry()
    return _global_registry
