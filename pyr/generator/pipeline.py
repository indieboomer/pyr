"""End-to-end generation pipeline: prompt → validated → tested → refined → game definition."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from pyr.generator.narrative import expand_game, generate_game, refine_game
from pyr.models.game import GameDefinition
from pyr.pipeline.tester import HeadlessTester
from pyr.pipeline.validator import GameValidator


class GenerationPipeline:
    def __init__(
        self,
        output_dir: Path,
        max_refinement_cycles: int = 3,
        progress_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.output_dir = output_dir
        self.max_refinement_cycles = max_refinement_cycles
        self.progress = progress_callback or print

    def run(self, prompt: str) -> GameDefinition:
        """Full pipeline: generate, validate, test, refine, save."""
        # Step 1: Generate
        self.progress("[1/5] Generating game from prompt...")
        game = generate_game(prompt, self.progress)
        self.progress(f"      Generated: '{game.title}' — {len(game.scenes)} scenes")

        # Step 2: Validate schema
        self.progress("[2/5] Validating game definition...")
        validator = GameValidator(game)
        errors = validator.validate()
        if errors:
            self.progress(f"      {len(errors)} validation error(s) — attempting refinement")
            game = refine_game(game, errors, self.progress)

        # Step 3: Headless test
        self.progress("[3/5] Running headless playthrough tests...")
        tester = HeadlessTester(game)
        results = tester.run()
        self.progress(f"      Coverage: {results.scene_coverage:.0%} | Issues: {len(results.issues)}")

        # Step 4: Auto-refine
        self.progress("[4/5] Refining game...")
        for cycle in range(self.max_refinement_cycles):
            if not results.issues:
                break
            self.progress(f"      Refinement cycle {cycle + 1}/{self.max_refinement_cycles}...")
            game = refine_game(game, results.issues, self.progress)
            tester = HeadlessTester(game)
            results = tester.run()
            self.progress(f"      After refinement — Coverage: {results.scene_coverage:.0%} | Issues: {len(results.issues)}")

        # Step 5: Save
        self.progress("[5/5] Saving game definition...")
        game_dir = self.output_dir / _slugify(game.title)
        game_dir.mkdir(parents=True, exist_ok=True)
        (game_dir / "game.json").write_text(game.model_dump_json(indent=2), encoding="utf-8")
        self.progress(f"      Saved to: {game_dir / 'game.json'}")

        return game

    def expand(self, game_dir: Path, expansion_prompt: str) -> GameDefinition:
        """Expand an existing game with new content."""
        game_json_path = game_dir / "game.json"
        if not game_json_path.exists():
            raise FileNotFoundError(f"No game.json found in {game_dir}")

        data = json.loads(game_json_path.read_text(encoding="utf-8"))
        game = GameDefinition.model_validate(data)

        self.progress("Expanding game...")
        game = expand_game(game, expansion_prompt, self.progress)

        game_json_path.write_text(game.model_dump_json(indent=2), encoding="utf-8")
        self.progress(f"Saved expanded game to {game_json_path}")
        return game


def _slugify(text: str) -> str:
    import re
    return re.sub(r"[^\w-]", "_", text.lower())[:40].strip("_")
