"""Asset manifest models — describes every graphic, audio, and voice asset a game needs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BackgroundAsset(BaseModel):
    id: str
    filename: str
    type: Literal["background"] = "background"
    used_in_scenes: list[str] = Field(default_factory=list)
    generation_prompt: str
    style_notes: str = ""


class PortraitAsset(BaseModel):
    id: str
    filename: str
    type: Literal["portrait"] = "portrait"
    character_id: str
    character_name: str
    mood: str
    generation_prompt: str
    style_notes: str = ""


class MusicAsset(BaseModel):
    id: str
    filename: str
    type: Literal["music"] = "music"
    used_in_scenes: list[str] = Field(default_factory=list)
    generation_prompt: str
    mood: str = ""
    loop: bool = True
    duration_seconds: int = 120


class SFXAsset(BaseModel):
    id: str
    filename: str
    type: Literal["sfx"] = "sfx"
    used_in_scenes: list[str] = Field(default_factory=list)
    generation_prompt: str
    style_notes: str = ""
    duration_seconds: float = 2.0


class BarkAsset(BaseModel):
    id: str
    filename: str
    type: Literal["bark"] = "bark"
    character_id: str
    character_name: str
    text: str
    generation_prompt: str
    voice_description: str = ""


class AssetManifest(BaseModel):
    game_title: str
    game_dir: str = ""
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    backgrounds: list[BackgroundAsset] = Field(default_factory=list)
    portraits: list[PortraitAsset] = Field(default_factory=list)
    music: list[MusicAsset] = Field(default_factory=list)
    sfx: list[SFXAsset] = Field(default_factory=list)
    barks: list[BarkAsset] = Field(default_factory=list)

    @property
    def total_count(self) -> int:
        return len(self.backgrounds) + len(self.portraits) + len(self.music) + len(self.sfx) + len(self.barks)

    def summary(self) -> dict[str, int]:
        return {
            "backgrounds": len(self.backgrounds),
            "portraits": len(self.portraits),
            "music": len(self.music),
            "sfx": len(self.sfx),
            "barks": len(self.barks),
            "total": self.total_count,
        }
