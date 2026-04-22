"""Pygame renderer for the narrative game runtime."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pyr.models.game import Choice, DialogueLine, GameDefinition, Scene

# ── Layout constants ──────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1280, 720
DIALOGUE_BOX_H = 240
CHOICE_BOX_H = 200

COLOR_BG = (15, 12, 20)
COLOR_DIALOGUE_BOX = (20, 16, 30, 220)
COLOR_CHOICE_BOX = (25, 20, 38, 200)
COLOR_CHOICE_HOVER = (60, 45, 90, 240)
COLOR_CHOICE_SELECTED = (90, 60, 130, 255)
COLOR_TEXT = (230, 220, 245)
COLOR_CHAR_NAME = (180, 140, 255)
COLOR_TITLE = (140, 100, 220)
COLOR_BORDER = (100, 70, 160)
COLOR_JOURNAL = (200, 190, 230)


class Renderer:
    def __init__(self, game: GameDefinition, assets_dir: Path | None = None) -> None:
        self.game = game
        self.assets_dir = assets_dir or Path("assets")
        self._bg_cache: dict[str, pygame.Surface] = {}
        self._portrait_cache: dict[str, pygame.Surface] = {}
        self._font_cache: dict[tuple, pygame.font.Font] = {}

        pygame.init()
        pygame.display.set_caption(game.title)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self._load_fonts()

    def _load_fonts(self) -> None:
        self.font_body = self._get_font(20)
        self.font_name = self._get_font(22, bold=True)
        self.font_choice = self._get_font(19)
        self.font_title = self._get_font(32, bold=True)
        self.font_small = self._get_font(15)

    def _get_font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self._font_cache:
            try:
                font_path = self.assets_dir / "fonts" / ("bold.ttf" if bold else "regular.ttf")
                if font_path.exists():
                    self._font_cache[key] = pygame.font.Font(str(font_path), size)
                else:
                    self._font_cache[key] = pygame.font.SysFont("segoeui" if bold else "segoeui", size, bold=bold)
            except Exception:
                self._font_cache[key] = pygame.font.Font(None, size + 4)
        return self._font_cache[key]

    def _get_background(self, name: str) -> pygame.Surface | None:
        if name in self._bg_cache:
            return self._bg_cache[name]
        for ext in (".png", ".jpg", ".jpeg"):
            path = self.assets_dir / "backgrounds" / f"{name}{ext}"
            if path.exists():
                surf = pygame.image.load(str(path)).convert()
                surf = pygame.transform.scale(surf, (SCREEN_W, SCREEN_H))
                self._bg_cache[name] = surf
                return surf
        return None

    def _get_portrait(self, character_id: str, mood: str | None = None) -> pygame.Surface | None:
        key = f"{character_id}_{mood or 'default'}"
        if key in self._portrait_cache:
            return self._portrait_cache[key]
        for name in [key, character_id]:
            for ext in (".png", ".jpg"):
                path = self.assets_dir / "portraits" / f"{name}{ext}"
                if path.exists():
                    surf = pygame.image.load(str(path)).convert_alpha()
                    h = DIALOGUE_BOX_H + 60
                    w = int(surf.get_width() * h / surf.get_height())
                    surf = pygame.transform.scale(surf, (w, h))
                    self._portrait_cache[key] = surf
                    return surf
        return None

    def render_scene(
        self,
        scene: "Scene",
        dialogue_index: int,
        choices: list["Choice"],
        hovered_choice: int,
        show_journal: bool = False,
        journal_entries: list | None = None,
    ) -> None:
        # Background
        bg = self._get_background(scene.background or "") if scene.background else None
        if bg:
            self.screen.blit(bg, (0, 0))
        else:
            self.screen.fill(COLOR_BG)

        dialogue_y = SCREEN_H - DIALOGUE_BOX_H - CHOICE_BOX_H - 10
        if scene.dialogue and dialogue_index < len(scene.dialogue):
            self._render_dialogue_box(scene.dialogue[dialogue_index], dialogue_y)

        if not scene.dialogue or dialogue_index >= len(scene.dialogue):
            self._render_choices(choices, hovered_choice)

        self._render_hud(scene)

        if show_journal and journal_entries:
            self._render_journal(journal_entries)

        pygame.display.flip()

    def _render_dialogue_box(self, line: "DialogueLine", y: int) -> None:
        box = pygame.Surface((SCREEN_W - 40, DIALOGUE_BOX_H), pygame.SRCALPHA)
        box.fill(COLOR_DIALOGUE_BOX)
        self.screen.blit(box, (20, SCREEN_H - DIALOGUE_BOX_H - 10))

        pygame.draw.rect(
            self.screen, COLOR_BORDER,
            (20, SCREEN_H - DIALOGUE_BOX_H - 10, SCREEN_W - 40, DIALOGUE_BOX_H),
            2, border_radius=8
        )

        x_offset = 30
        if line.character:
            char = self.game.characters.get(line.character)
            name = char.name if char else line.character
            portrait = self._get_portrait(line.character, line.portrait_mood)
            if portrait:
                px = 30
                py = SCREEN_H - DIALOGUE_BOX_H - 10 - 60
                self.screen.blit(portrait, (px, py))
                x_offset = portrait.get_width() + 50

            name_surf = self.font_name.render(name, True, COLOR_CHAR_NAME)
            self.screen.blit(name_surf, (x_offset, SCREEN_H - DIALOGUE_BOX_H))

        self._render_wrapped_text(
            line.text,
            x_offset,
            SCREEN_H - DIALOGUE_BOX_H + 30,
            SCREEN_W - x_offset - 60,
            COLOR_TEXT,
            self.font_body,
        )

        hint = self.font_small.render("[ SPACE / ENTER ] Continue", True, (120, 100, 150))
        self.screen.blit(hint, (SCREEN_W - hint.get_width() - 30, SCREEN_H - 30))

    def _render_choices(self, choices: list["Choice"], hovered: int) -> None:
        box_y = SCREEN_H - CHOICE_BOX_H - 10
        box = pygame.Surface((SCREEN_W - 40, CHOICE_BOX_H), pygame.SRCALPHA)
        box.fill(COLOR_CHOICE_BOX)
        self.screen.blit(box, (20, box_y))
        pygame.draw.rect(self.screen, COLOR_BORDER, (20, box_y, SCREEN_W - 40, CHOICE_BOX_H), 2, border_radius=8)

        item_h = 44
        padding = 12
        start_y = box_y + padding

        for i, choice in enumerate(choices):
            cy = start_y + i * item_h
            color = COLOR_CHOICE_HOVER if i == hovered else (40, 32, 55, 180)
            item_surf = pygame.Surface((SCREEN_W - 80, item_h - 4), pygame.SRCALPHA)
            item_surf.fill(color)
            self.screen.blit(item_surf, (30, cy))

            label = f"{i + 1}. {choice.text}"
            text_surf = self.font_choice.render(label, True, COLOR_TEXT)
            self.screen.blit(text_surf, (44, cy + 10))

        hint = self.font_small.render("[ ↑↓ ] Navigate   [ ENTER ] Select   [ J ] Journal", True, (120, 100, 150))
        self.screen.blit(hint, (SCREEN_W - hint.get_width() - 30, SCREEN_H - 30))

    def _render_hud(self, scene: "Scene") -> None:
        title_surf = self.font_small.render(scene.title, True, COLOR_TITLE)
        self.screen.blit(title_surf, (20, 12))

    def _render_journal(self, entries: list) -> None:
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((10, 8, 18, 210))
        self.screen.blit(overlay, (0, 0))

        title = self.font_title.render("Journal", True, COLOR_TITLE)
        self.screen.blit(title, (40, 30))

        y = 90
        for entry in entries[-12:]:
            t = self.font_name.render(entry.title, True, COLOR_CHAR_NAME)
            self.screen.blit(t, (40, y))
            y += 26
            self._render_wrapped_text(entry.text, 40, y, SCREEN_W - 80, COLOR_JOURNAL, self.font_small)
            y += 50

        hint = self.font_small.render("[ J ] Close Journal", True, (120, 100, 150))
        self.screen.blit(hint, (40, SCREEN_H - 30))

    def _render_wrapped_text(
        self, text: str, x: int, y: int, max_w: int, color: tuple, font: pygame.font.Font
    ) -> None:
        avg_char_w = font.size("x")[0]
        chars_per_line = max(1, max_w // avg_char_w)
        lines = textwrap.wrap(text, width=chars_per_line)
        line_h = font.get_linesize()
        for i, line in enumerate(lines):
            surf = font.render(line, True, color)
            self.screen.blit(surf, (x, y + i * line_h))

    def render_title_screen(self) -> None:
        self.screen.fill(COLOR_BG)
        title = self.font_title.render(self.game.title, True, COLOR_TITLE)
        desc = self.font_body.render(self.game.description[:80], True, COLOR_TEXT)
        hint = self.font_body.render("Press ENTER to start", True, (140, 120, 180))
        self.screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, SCREEN_H // 2 - 80))
        self.screen.blit(desc, (SCREEN_W // 2 - desc.get_width() // 2, SCREEN_H // 2))
        self.screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H // 2 + 80))
        pygame.display.flip()

    def render_ending_screen(self, scene_title: str, text: str) -> None:
        self.screen.fill((5, 3, 10))
        title = self.font_title.render(scene_title, True, COLOR_TITLE)
        hint = self.font_small.render("Press ESC to quit", True, (100, 80, 130))
        self.screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, SCREEN_H // 2 - 60))
        self._render_wrapped_text(text, 80, SCREEN_H // 2, SCREEN_W - 160, COLOR_TEXT, self.font_body)
        self.screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 40))
        pygame.display.flip()

    def quit(self) -> None:
        pygame.quit()
