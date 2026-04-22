"""Tests for core game data models."""

import json
from pathlib import Path

import pytest

from pyr.models.game import (
    Character,
    Choice,
    Condition,
    ConditionOp,
    Consequence,
    ConsequenceType,
    DialogueLine,
    GameDefinition,
    GameState,
    Scene,
    SystemConfig,
)

DEMO_GAME_PATH = Path(__file__).parent.parent / "games" / "demo" / "game.json"


def load_demo_game() -> GameDefinition:
    data = json.loads(DEMO_GAME_PATH.read_text(encoding="utf-8"))
    return GameDefinition.model_validate(data)


def test_demo_game_loads():
    game = load_demo_game()
    assert game.title == "Echoes of Ashford High"
    assert game.start_scene in game.scenes


def test_demo_game_has_endings():
    game = load_demo_game()
    endings = [s for s in game.scenes.values() if s.is_ending]
    assert len(endings) >= 2


def test_demo_game_all_scene_refs_valid():
    game = load_demo_game()
    scene_ids = set(game.scenes.keys())
    for scene in game.scenes.values():
        for choice in scene.choices:
            assert choice.next_scene in scene_ids, (
                f"Scene '{scene.id}' choice '{choice.id}' → unknown '{choice.next_scene}'"
            )


def test_initial_state():
    game = load_demo_game()
    state = game.make_initial_state()
    assert state.current_scene == game.start_scene
    assert isinstance(state.flags, dict)
    assert isinstance(state.inventory, list)


def test_condition_has():
    state = GameState(current_scene="x", inventory=["key"])
    cond = Condition(op=ConditionOp.has, target="key")
    assert state.is_condition_met(cond)
    cond2 = Condition(op=ConditionOp.has, target="sword")
    assert not state.is_condition_met(cond2)


def test_condition_knows():
    state = GameState(current_scene="x", flags={"met_mia": True})
    cond = Condition(op=ConditionOp.knows, target="met_mia")
    assert state.is_condition_met(cond)
    cond2 = Condition(op=ConditionOp.not_knows, target="met_mia")
    assert not state.is_condition_met(cond2)


def test_condition_numeric():
    state = GameState(current_scene="x", variables={"reputation": 15})
    assert state.is_condition_met(Condition(op=ConditionOp.gt, target="reputation", value=10))
    assert state.is_condition_met(Condition(op=ConditionOp.lte, target="reputation", value=15))
    assert not state.is_condition_met(Condition(op=ConditionOp.eq, target="reputation", value=10))


def test_consequence_set_flag():
    state = GameState(current_scene="x")
    c = Consequence(type=ConsequenceType.set_flag, target="found_clue")
    state.apply_consequence(c)
    assert state.flags["found_clue"] is True


def test_consequence_add_item():
    state = GameState(current_scene="x")
    c = Consequence(type=ConsequenceType.add_item, target="old_key")
    state.apply_consequence(c)
    assert "old_key" in state.inventory
    state.apply_consequence(c)
    assert state.inventory.count("old_key") == 1  # no duplicates


def test_consequence_add_var():
    state = GameState(current_scene="x", variables={"gold": 10})
    c = Consequence(type=ConsequenceType.add_var, target="gold", value=5)
    state.apply_consequence(c)
    assert state.variables["gold"] == 15


def test_scene_must_have_choices_or_be_ending():
    with pytest.raises(Exception):
        Scene(id="bad", title="Bad", dialogue=[], choices=[], is_ending=False)


def test_game_validates_start_scene():
    with pytest.raises(Exception):
        GameDefinition(
            title="Test",
            description="Test",
            start_scene="nonexistent",
            scenes={
                "real": Scene(
                    id="real", title="Real",
                    dialogue=[DialogueLine(text="fin")],
                    choices=[], is_ending=True
                )
            },
        )
