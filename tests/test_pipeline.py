"""Tests for validator and headless tester."""

import json
from pathlib import Path

from pyr.models.game import GameDefinition
from pyr.pipeline.tester import HeadlessTester
from pyr.pipeline.validator import GameValidator

DEMO_GAME_PATH = Path(__file__).parent.parent / "games" / "demo" / "game.json"


def load_demo_game() -> GameDefinition:
    data = json.loads(DEMO_GAME_PATH.read_text(encoding="utf-8"))
    return GameDefinition.model_validate(data)


def test_validator_passes_demo():
    game = load_demo_game()
    validator = GameValidator(game)
    errors = validator.validate()
    assert errors == [], f"Validation errors: {errors}"


def test_headless_tester_runs():
    game = load_demo_game()
    tester = HeadlessTester(game, playthroughs=10, max_steps=100)
    results = tester.run()
    assert results.playthrough_count == 10
    assert len(results.scenes_reached) > 0
    assert len(results.endings_reached) > 0
    assert results.scene_coverage > 0


def test_headless_tester_finds_endings():
    game = load_demo_game()
    tester = HeadlessTester(game, playthroughs=30, max_steps=200)
    results = tester.run()
    assert len(results.endings_reached) >= 2, f"Only reached endings: {results.endings_reached}"


def test_headless_tester_no_issues_on_demo():
    game = load_demo_game()
    tester = HeadlessTester(game, playthroughs=20, max_steps=200)
    results = tester.run()
    assert results.issues == [], f"Issues found: {results.issues}"


def test_replay_log():
    game = load_demo_game()
    tester = HeadlessTester(game)
    log = tester.replay_log()
    assert len(log) > 0
    assert log[0]["scene"] == game.start_scene
    assert log[-1]["is_ending"] or len(log) == tester.max_steps
