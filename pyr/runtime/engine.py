"""Main game engine — event loop, input handling, and game flow."""

from __future__ import annotations

from pathlib import Path

import pygame

from pyr.models.game import GameDefinition
from pyr.runtime.renderer import Renderer
from pyr.runtime.state_manager import StateManager


class GameEngine:
    def __init__(self, game: GameDefinition, assets_dir: Path | None = None, save_dir: Path | None = None) -> None:
        self.game = game
        self.state_manager = StateManager(game)
        self.renderer = Renderer(game, assets_dir)
        self.save_dir = save_dir or Path("saves")
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self._running = False
        self._dialogue_index = 0
        self._hovered_choice = 0
        self._show_journal = False
        self._title_screen = True

    def run(self) -> None:
        self._running = True
        self.renderer.render_title_screen()

        while self._running:
            self.renderer.clock.tick(60)
            for event in pygame.event.get():
                self._handle_event(event)

        self.renderer.quit()

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return

        if event.type != pygame.KEYDOWN:
            return

        key = event.key

        if key == pygame.K_ESCAPE:
            self._running = False
            return

        if self._title_screen:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self._title_screen = False
                self._render_current()
            return

        if self.state_manager.is_game_over():
            return

        scene = self.state_manager.current_scene

        # Journal toggle
        if key == pygame.K_j:
            self._show_journal = not self._show_journal
            self._render_current()
            return

        self._show_journal = False

        # Save/Load
        if key == pygame.K_F5:
            self.state_manager.save(self.save_dir / "quicksave.json")
            return
        if key == pygame.K_F9:
            save_path = self.save_dir / "quicksave.json"
            if save_path.exists():
                self.state_manager.load(save_path)
                self._dialogue_index = 0
                self._render_current()
            return

        # Advance dialogue
        if self._dialogue_index < len(scene.dialogue):
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self._dialogue_index += 1
                self._render_current()
            return

        # Choice navigation
        choices = self.state_manager.available_choices()
        if not choices:
            return

        if key == pygame.K_UP:
            self._hovered_choice = max(0, self._hovered_choice - 1)
        elif key == pygame.K_DOWN:
            self._hovered_choice = min(len(choices) - 1, self._hovered_choice + 1)
        elif key in (pygame.K_1, pygame.K_KP1):
            self._hovered_choice = 0
        elif key in (pygame.K_2, pygame.K_KP2) and len(choices) > 1:
            self._hovered_choice = 1
        elif key in (pygame.K_3, pygame.K_KP3) and len(choices) > 2:
            self._hovered_choice = 2
        elif key in (pygame.K_4, pygame.K_KP4) and len(choices) > 3:
            self._hovered_choice = 3
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            self._select_choice(choices[self._hovered_choice])
            return

        self._render_current()

    def _select_choice(self, choice) -> None:
        self.state_manager.apply_choice(choice)
        self._dialogue_index = 0
        self._hovered_choice = 0

        if self.state_manager.is_game_over():
            scene = self.state_manager.current_scene
            text = scene.dialogue[0].text if scene.dialogue else "The end."
            self.renderer.render_ending_screen(scene.title, text)
        else:
            self._render_current()

    def _render_current(self) -> None:
        scene = self.state_manager.current_scene
        choices = self.state_manager.available_choices()
        self.renderer.render_scene(
            scene=scene,
            dialogue_index=self._dialogue_index,
            choices=choices,
            hovered_choice=self._hovered_choice,
            show_journal=self._show_journal,
            journal_entries=self.state_manager.state.journal,
        )
