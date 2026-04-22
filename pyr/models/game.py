"""Core game data models — the single source of truth for all game definitions."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ConditionOp(str, Enum):
    eq = "eq"
    ne = "ne"
    gt = "gt"
    lt = "lt"
    gte = "gte"
    lte = "lte"
    has = "has"       # item in inventory
    knows = "knows"   # flag is True
    not_knows = "not_knows"


class Condition(BaseModel):
    op: ConditionOp
    target: str                        # variable name, flag name, or item id
    value: int | float | str | None = None


class ConsequenceType(str, Enum):
    set_flag = "set_flag"
    clear_flag = "clear_flag"
    set_var = "set_var"
    add_var = "add_var"
    add_item = "add_item"
    remove_item = "remove_item"
    set_relationship = "set_relationship"
    add_relationship = "add_relationship"
    add_journal = "add_journal"


class Consequence(BaseModel):
    type: ConsequenceType
    target: str
    value: int | float | str | bool | None = None
    character: str | None = None      # for relationship consequences


class Choice(BaseModel):
    id: str
    text: str
    conditions: list[Condition] = Field(default_factory=list)
    consequences: list[Consequence] = Field(default_factory=list)
    next_scene: str


class Event(BaseModel):
    trigger: Literal["on_enter", "on_exit", "on_choice"] = "on_enter"
    conditions: list[Condition] = Field(default_factory=list)
    consequences: list[Consequence] = Field(default_factory=list)
    redirect_scene: str | None = None


class DialogueLine(BaseModel):
    character: str | None = None      # None = narrator
    text: str
    portrait_mood: str | None = None  # e.g. "happy", "angry"


class Scene(BaseModel):
    id: str
    title: str
    background: str | None = None
    ambient_music: str | None = None
    dialogue: list[DialogueLine] = Field(default_factory=list)
    choices: list[Choice] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    is_ending: bool = False

    @model_validator(mode="after")
    def validate_scene(self) -> Scene:
        if not self.is_ending and not self.choices:
            raise ValueError(f"Scene '{self.id}' has no choices and is not an ending")
        return self


class CharacterTrait(BaseModel):
    name: str
    value: str


class Character(BaseModel):
    id: str
    name: str
    traits: list[CharacterTrait] = Field(default_factory=list)
    portrait: str | None = None
    initial_relationships: dict[str, int] = Field(default_factory=dict)
    description: str = ""
    voice_description: str = ""  # e.g. "soft British accent, mid-30s woman, warm but guarded"

    @field_validator("initial_relationships", mode="before")
    @classmethod
    def coerce_relationship_values(cls, v: object) -> object:
        if not isinstance(v, dict):
            return v
        result: dict[str, int] = {}
        for k, val in v.items():
            if isinstance(val, int):
                result[k] = val
            elif isinstance(val, float):
                result[k] = int(val)
            elif isinstance(val, str):
                try:
                    result[k] = int(val)
                except ValueError:
                    result[k] = 0  # non-numeric strings like "neutral" → 0
            else:
                result[k] = 0
        return result


class SystemConfig(BaseModel):
    initial_flags: dict[str, bool] = Field(default_factory=dict)
    initial_variables: dict[str, int | float] = Field(default_factory=dict)
    initial_inventory: list[str] = Field(default_factory=list)
    resource_definitions: dict[str, dict[str, Any]] = Field(default_factory=dict)


class JournalEntry(BaseModel):
    type: Literal["clue", "event", "conversation"] = "event"
    title: str
    text: str
    scene_id: str | None = None


class GameState(BaseModel):
    current_scene: str
    flags: dict[str, bool] = Field(default_factory=dict)
    variables: dict[str, int | float] = Field(default_factory=dict)
    inventory: list[str] = Field(default_factory=list)
    relationships: dict[str, dict[str, int]] = Field(default_factory=dict)
    journal: list[JournalEntry] = Field(default_factory=list)
    visited_scenes: list[str] = Field(default_factory=list)
    choice_history: list[dict[str, str]] = Field(default_factory=list)

    def is_condition_met(self, condition: Condition) -> bool:
        op = condition.op
        target = condition.target
        val = condition.value

        if op == ConditionOp.has:
            return target in self.inventory
        if op == ConditionOp.knows:
            return self.flags.get(target, False)
        if op == ConditionOp.not_knows:
            return not self.flags.get(target, False)

        current = self.variables.get(target, 0)
        if op == ConditionOp.eq:
            return current == val
        if op == ConditionOp.ne:
            return current != val
        if op == ConditionOp.gt:
            return current > val
        if op == ConditionOp.lt:
            return current < val
        if op == ConditionOp.gte:
            return current >= val
        if op == ConditionOp.lte:
            return current <= val
        return False

    def apply_consequence(self, consequence: Consequence) -> None:
        t = consequence.type
        target = consequence.target
        value = consequence.value

        if t == ConsequenceType.set_flag:
            self.flags[target] = True
        elif t == ConsequenceType.clear_flag:
            self.flags[target] = False
        elif t == ConsequenceType.set_var:
            self.variables[target] = value
        elif t == ConsequenceType.add_var:
            self.variables[target] = self.variables.get(target, 0) + value
        elif t == ConsequenceType.add_item:
            if target not in self.inventory:
                self.inventory.append(target)
        elif t == ConsequenceType.remove_item:
            self.inventory = [i for i in self.inventory if i != target]
        elif t == ConsequenceType.set_relationship:
            char = consequence.character or target
            if char not in self.relationships:
                self.relationships[char] = {}
            self.relationships[char][target] = value
        elif t == ConsequenceType.add_relationship:
            char = consequence.character
            if char not in self.relationships:
                self.relationships[char] = {}
            self.relationships[char][target] = self.relationships[char].get(target, 0) + value
        elif t == ConsequenceType.add_journal:
            self.journal.append(JournalEntry(title=target, text=str(value)))


class GameDefinition(BaseModel):
    title: str
    description: str
    author: str = "PYR"
    version: str = "1.0"
    start_scene: str
    scenes: dict[str, Scene]
    characters: dict[str, Character] = Field(default_factory=dict)
    systems: SystemConfig = Field(default_factory=SystemConfig)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_references(self) -> GameDefinition:
        scene_ids = set(self.scenes.keys())

        if self.start_scene not in scene_ids:
            raise ValueError(f"start_scene '{self.start_scene}' not found in scenes")

        for scene in self.scenes.values():
            for choice in scene.choices:
                if choice.next_scene not in scene_ids:
                    raise ValueError(
                        f"Scene '{scene.id}' choice '{choice.id}' references unknown scene '{choice.next_scene}'"
                    )
            for event in scene.events:
                if event.redirect_scene and event.redirect_scene not in scene_ids:
                    raise ValueError(
                        f"Scene '{scene.id}' event references unknown scene '{event.redirect_scene}'"
                    )

        return self

    def make_initial_state(self) -> GameState:
        state = GameState(
            current_scene=self.start_scene,
            flags=dict(self.systems.initial_flags),
            variables=dict(self.systems.initial_variables),
            inventory=list(self.systems.initial_inventory),
        )
        for char in self.characters.values():
            if char.initial_relationships:
                state.relationships[char.id] = dict(char.initial_relationships)
        return state
