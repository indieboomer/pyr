"""Asset manifest generator — asks Claude to produce generation prompts for every game asset."""

from __future__ import annotations

import json

from pyr.generator.narrative import _call_claude, _extract_json
from pyr.generator.prompts import ASSET_MANIFEST_SYSTEM
from pyr.models.assets import AssetManifest
from pyr.models.game import GameDefinition


def generate_asset_manifest(
    game: GameDefinition,
    game_dir: str = "",
    progress_callback=None,
) -> AssetManifest:
    """Analyze a game definition and produce a full asset manifest with generation prompts."""
    if progress_callback:
        progress_callback("Analyzing game and generating asset manifest via Claude...")

    game_json = game.model_dump_json(indent=2)
    user_message = (
        f"Game definition:\n{game_json}\n\n"
        f"Produce the complete asset manifest for this game. "
        f"Every background, character portrait (all moods), music track, sound effect, "
        f"and character bark must have a detailed, actionable generation prompt. "
        f"Return only valid JSON."
    )

    raw = _extract_json(_call_claude(ASSET_MANIFEST_SYSTEM, user_message))
    data = json.loads(raw)

    return AssetManifest(
        game_title=game.title,
        game_dir=game_dir,
        **data,
    )
