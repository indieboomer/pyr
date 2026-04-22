"""Game definition validator — catches structural errors before runtime."""

from __future__ import annotations

from pyr.models.game import GameDefinition


class GameValidator:
    def __init__(self, game: GameDefinition) -> None:
        self.game = game

    def validate(self) -> list[str]:
        errors: list[str] = []
        scene_ids = set(self.game.scenes.keys())
        char_ids = set(self.game.characters.keys())

        if self.game.start_scene not in scene_ids:
            errors.append(f"start_scene '{self.game.start_scene}' does not exist")

        for scene_id, scene in self.game.scenes.items():
            if not scene.is_ending and not scene.choices:
                errors.append(f"Scene '{scene_id}' has no choices and is not an ending")

            if scene.is_ending and not scene.dialogue:
                errors.append(f"Ending scene '{scene_id}' has no dialogue")

            for choice in scene.choices:
                if choice.next_scene not in scene_ids:
                    errors.append(
                        f"Scene '{scene_id}' choice '{choice.id}' references unknown scene '{choice.next_scene}'"
                    )
                for cond in choice.conditions:
                    pass  # variable names are dynamic; skip deep validation

            for event in scene.events:
                if event.redirect_scene and event.redirect_scene not in scene_ids:
                    errors.append(
                        f"Scene '{scene_id}' event redirects to unknown scene '{event.redirect_scene}'"
                    )

            for line in scene.dialogue:
                if line.character and line.character not in char_ids:
                    errors.append(
                        f"Scene '{scene_id}' dialogue references unknown character '{line.character}'"
                    )

        return errors

    def report(self) -> str:
        errors = self.validate()
        if not errors:
            return "Validation passed — no errors found."
        lines = [f"Validation failed — {len(errors)} error(s):"]
        for e in errors:
            lines.append(f"  - {e}")
        return "\n".join(lines)
