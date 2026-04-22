"""Headless game tester — simulates playthroughs to find dead ends, broken logic, and coverage gaps."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from pyr.models.game import GameDefinition, ConditionOp
from pyr.runtime.state_manager import StateManager


@dataclass
class TestResult:
    scenes_reached: set[str] = field(default_factory=set)
    endings_reached: set[str] = field(default_factory=set)
    issues: list[str] = field(default_factory=list)
    playthrough_count: int = 0

    def __post_init__(self):
        self._total_scenes = 0

    def compute_coverage(self, total: int) -> None:
        self._total_scenes = total

    @property
    def scene_coverage(self) -> float:
        if not self._total_scenes:
            return 0.0
        return len(self.scenes_reached) / self._total_scenes


class HeadlessTester:
    def __init__(self, game: GameDefinition, playthroughs: int = 20, max_steps: int = 200) -> None:
        self.game = game
        self.playthroughs = playthroughs
        self.max_steps = max_steps

    def run(self) -> TestResult:
        result = TestResult()
        all_scene_ids = set(self.game.scenes.keys())

        # Collect all flags used in conditions across the game
        all_flags = self._collect_all_condition_flags()

        # Random playthroughs
        for _ in range(self.playthroughs):
            self._simulate_playthrough(result)
            result.playthrough_count += 1

        # Extra targeted playthroughs with all flags pre-set to explore every conditional branch
        for _ in range(min(self.playthroughs, 10)):
            self._simulate_playthrough(result, force_flags=all_flags)

        result.compute_coverage(len(all_scene_ids))

        # Structural: scenes that are structurally unreachable (no choice points to them)
        structurally_reachable = self._find_structurally_reachable()
        unreachable = all_scene_ids - structurally_reachable
        for scene_id in unreachable:
            result.issues.append(f"Scene '{scene_id}' is unreachable (no path leads to it)")

        # Dead-end scenes
        for scene_id, scene in self.game.scenes.items():
            if not scene.is_ending and not scene.choices:
                result.issues.append(f"Scene '{scene_id}' is a dead end (no choices, not an ending)")

        if not result.endings_reached:
            result.issues.append("No ending scenes were reached in any playthrough")

        return result

    def _collect_all_condition_flags(self) -> dict[str, bool]:
        """Collect every flag name used in any condition and pre-set them all to True."""
        flags: dict[str, bool] = {}
        for scene in self.game.scenes.values():
            for choice in scene.choices:
                for cond in choice.conditions:
                    if cond.op in (ConditionOp.knows, ConditionOp.not_knows):
                        flags[cond.target] = True
            for event in scene.events:
                for cond in event.conditions:
                    if cond.op in (ConditionOp.knows, ConditionOp.not_knows):
                        flags[cond.target] = True
        return flags

    def _find_structurally_reachable(self) -> set[str]:
        """BFS over all choices (ignoring conditions) to find structurally reachable scenes."""
        reachable: set[str] = {self.game.start_scene}
        queue = [self.game.start_scene]
        while queue:
            current = queue.pop()
            scene = self.game.scenes.get(current)
            if not scene:
                continue
            for choice in scene.choices:
                if choice.next_scene not in reachable:
                    reachable.add(choice.next_scene)
                    queue.append(choice.next_scene)
            for event in scene.events:
                if event.redirect_scene and event.redirect_scene not in reachable:
                    reachable.add(event.redirect_scene)
                    queue.append(event.redirect_scene)
        return reachable

    def _simulate_playthrough(self, result: TestResult, force_flags: dict | None = None) -> None:
        manager = StateManager(self.game)

        if force_flags:
            manager.state.flags.update(force_flags)

        for _ in range(self.max_steps):
            scene_id = manager.state.current_scene
            result.scenes_reached.add(scene_id)

            if manager.is_game_over():
                result.endings_reached.add(scene_id)
                return

            choices = manager.available_choices()
            if not choices:
                return

            # Prefer unvisited next scenes for better coverage
            unvisited = [c for c in choices if c.next_scene not in manager.state.visited_scenes]
            chosen = random.choice(unvisited) if unvisited else random.choice(choices)
            manager.apply_choice(chosen)

    def replay_log(self) -> list[dict]:
        """Generate a single deterministic replay log for debugging."""
        manager = StateManager(self.game)
        log = []

        for _ in range(self.max_steps):
            scene_id = manager.state.current_scene
            scene = self.game.scenes[scene_id]
            choices = manager.available_choices()

            log.append({
                "scene": scene_id,
                "title": scene.title,
                "choices": [c.text for c in choices],
                "is_ending": scene.is_ending,
            })

            if manager.is_game_over() or not choices:
                break

            manager.apply_choice(choices[0])

        return log
