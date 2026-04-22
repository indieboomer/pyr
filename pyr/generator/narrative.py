"""Narrative generator — calls the `claude` CLI (uses your Claude account, no API key needed)."""

from __future__ import annotations

import json
import re
import subprocess
import sys

from pyr.generator.prompts import GAME_GRAMMAR_SYSTEM, NARRATIVE_EXPANSION_SYSTEM, REFINER_SYSTEM
from pyr.models.game import GameDefinition

_MODEL = "claude-opus-4-7"


def _call_claude(system_prompt: str, user_message: str) -> str:
    """Call the claude CLI in print mode and return the text response.

    Passes the full prompt via stdin to avoid Windows argument escaping issues
    with long system prompts containing special characters.
    """
    combined = f"{system_prompt}\n\n---\n\n{user_message}"
    result = subprocess.run(
        [
            "claude", "-p",
            "--model", _MODEL,
            "--tools", "",
            "--no-session-persistence",
        ],
        input=combined,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI error (exit {result.returncode}):\n{result.stderr.strip()}")
    return result.stdout.strip()


def _extract_json(text: str) -> str:
    """Strip markdown fences if present."""
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        return match.group(1)
    return text.strip()


def generate_game(prompt: str, progress_callback=None) -> GameDefinition:
    """Generate a complete game definition from a natural language prompt."""
    if progress_callback:
        progress_callback("Generating narrative structure via Claude...")

    user_message = (
        f"Generate a complete narrative game based on this prompt:\n\n"
        f"\"{prompt}\"\n\n"
        f"Create an engaging game with branching storylines, memorable characters, "
        f"meaningful choices, and multiple distinct endings. "
        f"Include light systemic mechanics (relationships, at least one resource variable). "
        f"Return only valid JSON."
    )

    raw = _extract_json(_call_claude(GAME_GRAMMAR_SYSTEM, user_message))
    data = json.loads(raw)
    return GameDefinition.model_validate(data)


def expand_game(game: GameDefinition, expansion_prompt: str, progress_callback=None) -> GameDefinition:
    """Expand an existing game with new content based on a prompt."""
    if progress_callback:
        progress_callback("Expanding game content via Claude...")

    existing_json = game.model_dump_json(indent=2)
    user_message = (
        f"Existing game:\n```json\n{existing_json}\n```\n\n"
        f"Expansion request: {expansion_prompt}\n\n"
        f"Return the complete updated game JSON."
    )

    raw = _extract_json(_call_claude(NARRATIVE_EXPANSION_SYSTEM, user_message))
    data = json.loads(raw)
    return GameDefinition.model_validate(data)


def refine_game(game: GameDefinition, issues: list[str], progress_callback=None) -> GameDefinition:
    """Auto-fix game issues found by the tester."""
    if not issues:
        return game

    if progress_callback:
        progress_callback(f"Auto-fixing {len(issues)} issue(s) via Claude...")

    issues_text = "\n".join(f"- {issue}" for issue in issues)
    game_json = game.model_dump_json(indent=2)
    user_message = (
        f"Game definition:\n```json\n{game_json}\n```\n\n"
        f"Issues to fix:\n{issues_text}\n\n"
        f"Return the corrected complete game JSON."
    )

    raw = _extract_json(_call_claude(REFINER_SYSTEM, user_message))
    data = json.loads(raw)
    return GameDefinition.model_validate(data)
