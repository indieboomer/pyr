"""Game state manager — handles state transitions and persistence."""

from __future__ import annotations

import json
from pathlib import Path

from pyr.models.game import Choice, GameDefinition, GameState


class StateManager:
    def __init__(self, game: GameDefinition) -> None:
        self.game = game
        self.state = game.make_initial_state()
        self._on_scene_enter(self.state.current_scene)

    @property
    def current_scene(self):
        return self.game.scenes[self.state.current_scene]

    def available_choices(self) -> list[Choice]:
        return [
            c for c in self.current_scene.choices
            if all(self.state.is_condition_met(cond) for cond in c.conditions)
        ]

    def apply_choice(self, choice: Choice) -> None:
        for consequence in choice.consequences:
            self.state.apply_consequence(consequence)
        self.state.choice_history.append(
            {"scene": self.state.current_scene, "choice": choice.id}
        )
        self._transition_to(choice.next_scene)

    def _transition_to(self, scene_id: str) -> None:
        self._on_scene_exit(self.state.current_scene)
        self.state.current_scene = scene_id
        if scene_id not in self.state.visited_scenes:
            self.state.visited_scenes.append(scene_id)
        self._on_scene_enter(scene_id)

    def _on_scene_enter(self, scene_id: str) -> None:
        scene = self.game.scenes[scene_id]
        for event in scene.events:
            if event.trigger == "on_enter":
                if all(self.state.is_condition_met(c) for c in event.conditions):
                    for consequence in event.consequences:
                        self.state.apply_consequence(consequence)
                    if event.redirect_scene:
                        self._transition_to(event.redirect_scene)
                        return

    def _on_scene_exit(self, scene_id: str) -> None:
        scene = self.game.scenes[scene_id]
        for event in scene.events:
            if event.trigger == "on_exit":
                if all(self.state.is_condition_met(c) for c in event.conditions):
                    for consequence in event.consequences:
                        self.state.apply_consequence(consequence)

    def is_game_over(self) -> bool:
        return self.current_scene.is_ending

    def save(self, path: Path) -> None:
        path.write_text(self.state.model_dump_json(indent=2), encoding="utf-8")

    def load(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        self.state = GameState.model_validate(data)
