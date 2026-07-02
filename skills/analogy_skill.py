"""
skills/analogy_skill.py — Analogy-first teaching skill
"""

from __future__ import annotations

from typing import Any


def analogy_handler(
    topic: str,
    mastery_score: float,
    user_input: str,
    **kwargs: Any,
) -> str:
    """
    Build an analogy-based teaching prompt for the given topic.
    Used for students with mastery_score < 0.3.
    """
    analogies: dict[str, str] = {
        "variables": (
            "Think of a variable like a labeled box 📦. "
            "You write a label on the outside (the variable name) and put something inside (the value). "
            "You can always look inside or swap out the contents!"
        ),
        "data_types": (
            "Data types are like different kinds of containers in a kitchen. "
            "A jar (string) holds text/characters, a measuring cup (int/float) holds numbers, "
            "and a checklist (bool) is either checked or unchecked. "
            "Python needs to know what container you're using!"
        ),
        "loops": (
            "A loop is like a recipe instruction that says 'repeat until done'. "
            "Imagine you're washing dishes: 'Pick up dish → wash → rinse → repeat until no dishes left'. "
            "That's a for-loop! A while-loop says 'keep going while the sink is full'."
        ),
        "functions": (
            "A function is like a recipe card 🍳. "
            "You write the steps once (define), then you can cook that dish anytime by just calling its name. "
            "You can even pass in different ingredients (parameters) each time!"
        ),
        "control_flow": (
            "Control flow is like a Choose Your Own Adventure book 📖. "
            "If-elif-else are the 'decision points' where the story branches. "
            "Your code reads conditions and takes different paths based on what's true."
        ),
        "lists": (
            "A list is like a numbered shopping list 🛒. "
            "Item 0 is the first thing, item 1 is the second, and so on. "
            "You can add items, remove items, or check what's at a specific position."
        ),
        "dictionaries": (
            "A dictionary is like... well, a dictionary! 📖 "
            "Each word (key) has a definition (value). "
            "You look up by the key, not by position. Perfect for when you need labels, not numbers."
        ),
        "oop_basics": (
            "Object-Oriented Programming is like a blueprint factory 🏭. "
            "A class is the blueprint (e.g., 'Car'). "
            "Each object is a specific car built from that blueprint — same structure, different details."
        ),
        "error_handling": (
            "Error handling is like a safety net 🎪. "
            "try: is 'attempt the trick'. except: is 'catch me if I fall'. "
            "finally: is 'do this no matter what'. You don't plan to fail, but you plan for it!"
        ),
    }

    analogy = analogies.get(topic, f"Let me think of a great analogy for {topic}...")
    return (
        f"Let me start with an analogy that might help! 🎯\n\n"
        f"{analogy}\n\n"
        f"**Now, thinking about that analogy:** {user_input}\n\n"
        f"What part of this analogy connects with what you're trying to do? "
        f"Or what feels confusing about it?"
    )
