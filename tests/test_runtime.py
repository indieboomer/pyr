"""Tests for the state manager (runtime logic, no pygame required)."""

import json
from pathlib import Path

from pyr.models.game import GameDefinition
from pyr.runtime.state_manager import StateManager

DEMO_GAME_PATH = Path(__file__).parent.parent / "games" / "demo" / "game.json"


def load_demo_game() -> GameDefinition:
    data = json.loads(DEMO_GAME_PATH.read_text(encoding="utf-8"))
    return GameDefinition.model_validate(data)


def test_state_manager_starts_correctly():
    game = load_demo_game()
    sm = StateManager(game)
    assert sm.state.current_scene == game.start_scene
    assert not sm.is_game_over()


def test_available_choices_at_start():
    game = load_demo_game()
    sm = StateManager(game)
    choices = sm.available_choices()
    assert len(choices) > 0


def test_apply_choice_transitions_scene():
    game = load_demo_game()
    sm = StateManager(game)
    choices = sm.available_choices()
    initial_scene = sm.state.current_scene
    sm.apply_choice(choices[0])
    assert sm.state.current_scene != initial_scene


def test_conditional_choice_hidden_without_flag():
    game = load_demo_game()
    sm = StateManager(game)

    # Navigate to after_school_crossroads without setting the investigate flag
    sm.state.current_scene = "after_school_crossroads"
    choices = sm.available_choices()
    choice_ids = [c.id for c in choices]

    # investigate_east_wing requires curious_about_east_wing flag
    assert "investigate_east_wing" not in choice_ids


def test_conditional_choice_shown_with_flag():
    game = load_demo_game()
    sm = StateManager(game)

    sm.state.current_scene = "after_school_crossroads"
    sm.state.flags["curious_about_east_wing"] = True
    choices = sm.available_choices()
    choice_ids = [c.id for c in choices]
    assert "investigate_east_wing" in choice_ids


def test_save_load(tmp_path):
    game = load_demo_game()
    sm = StateManager(game)

    choices = sm.available_choices()
    sm.apply_choice(choices[0])
    sm.state.flags["test_flag"] = True

    save_path = tmp_path / "save.json"
    sm.save(save_path)

    sm2 = StateManager(game)
    sm2.load(save_path)
    assert sm2.state.current_scene == sm.state.current_scene
    assert sm2.state.flags.get("test_flag") is True


def test_game_over_at_ending():
    game = load_demo_game()
    sm = StateManager(game)
    sm.state.current_scene = "truth_ending"
    assert sm.is_game_over()
