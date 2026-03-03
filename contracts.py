"""Cross-module data contracts for the Adaptive AI Dungeon Master.

This module defines the only shared payload formats for scene generation,
resolution outputs, and AI observation data. Other modules should import these
types instead of redefining 'dict' schemas.
"""

from __future__ import annotations

import math
from typing import Any, Literal, TypedDict

BeatType = Literal[
    "exploration",
    "combat",
    "social",
    "mystery",
    "recovery",
    "revelation",
    "travel",
]

ActionType = Literal[
    "attack",
    "defend",
    "talk",
    "investigate",
    "explore",
    "use_item",
    "retreat",
    "wait",
]

_BEAT_TYPES = frozenset(
    {
        "exploration",
        "combat",
        "social",
        "mystery",
        "recovery",
        "revelation",
        "travel",
    }
)

_ACTION_TYPES = frozenset(
    {
        "attack",
        "defend",
        "talk",
        "investigate",
        "explore",
        "use_item",
        "retreat",
        "wait",
    }
)

_SCENE_SPEC_KEYS = frozenset(
    {
        "scene_id",
        "beat_type",
        "template_id",
        "template_group",
        "text_vars",
        "choices",
        "choice_text",
        "tags",
        "location_id",
        "difficulty",
        "thread_ids",
        "metadata",
    }
)

_OBSERVATION_KEYS = frozenset(
    {
        "choice",
        "choice_tags",
        "risk_level",
        "social_intent",
        "exploration_intent",
        "aggression_signal",
        "success",
        "failure",
        "metadata",
    }
)

_OUTCOME_KEYS = frozenset(
    {
        "player",
        "inventory_add",
        "inventory_remove",
        "flags",
        "relationships",
        "tension_delta",
        "plot_threads",
        "world_facts",
        "events",
        "success",
        "difficulty_signal",
        "metadata",
    }
)


class SceneSpec(TypedDict, total=False):
    """
    scene selection artifact produced by DMPolicy

    The format is intentionally permissive (total=False) in the skeleton so
    modules can share a common contract before the course team finalizes a
    stricter scheme. Implementations should converge on stable required fields.
    """

    scene_id: str
    beat_type: BeatType
    template_id: str
    template_group: str
    text_vars: dict[str, Any]
    choices: list[ActionType]
    choice_text: dict[str, str]
    tags: list[str]
    location_id: str
    difficulty: float
    thread_ids: list[str]
    metadata: dict[str, Any]


class Observation(TypedDict, total=False):
    """
    player-behavior evidence payload consumed by PlayerModel.

    Observations describe the player's decision style and contextual signals.
    They do not apply world mutations.
    """

    choice: ActionType
    choice_tags: list[str]
    risk_level: float
    social_intent: float
    exploration_intent: float
    aggression_signal: float
    success: bool
    failure: bool
    metadata: dict[str, Any]


class Outcome(TypedDict, total=False):
    """
    resolver delta payload applied by GameState.apply_outcome(...).

    Outcomes must contain deltas only and no direct mutable state objects.
    """

    player: dict[str, Any]
    inventory_add: list[str]
    inventory_remove: list[str]
    flags: dict[str, bool]
    relationships: dict[str, float]
    tension_delta: float
    plot_threads: list[dict[str, Any]]
    world_facts: dict[str, Any]
    events: list[dict[str, Any]]
    success: bool
    difficulty_signal: float
    metadata: dict[str, Any]


def validate_scene_spec(scene_spec: SceneSpec) -> None:
    """
    Stub validator for SceneSpec payloads crossing module boundaries.

    Args:
        scene_spec: Scene specification to validate.

    Returns:
        None.

    Interaction:
        Future implementation should enforce required keys, value types, and
        consistency constraints before downstream modules consume the payload.
    """
    if not isinstance(scene_spec, dict):
        raise TypeError("scene_spec must be a dict")

    for key in scene_spec:
        if key not in _SCENE_SPEC_KEYS:
            raise ValueError(f"scene_spec contains unknown key: {key!r}")

    if "beat_type" not in scene_spec:
        raise KeyError("scene_spec missing required key: 'beat_type'")

    beat_type = scene_spec["beat_type"]
    if not isinstance(beat_type, str):
        raise TypeError("scene_spec['beat_type'] must be a str")
    if beat_type not in _BEAT_TYPES:
        raise ValueError(f"scene_spec['beat_type'] is invalid: {beat_type!r}")

    for key in ("scene_id", "template_id", "template_group", "location_id"):
        if key in scene_spec:
            value = scene_spec[key]
            if not isinstance(value, str):
                raise TypeError(f"scene_spec[{key!r}] must be a str")
            if not value:
                raise ValueError(f"scene_spec[{key!r}] must be non-empty")

    for key in ("text_vars", "metadata"):
        if key in scene_spec and not isinstance(scene_spec[key], dict):
            raise TypeError(f"scene_spec[{key!r}] must be a dict")

    choices_set: set[str] | None = None
    if "choices" in scene_spec:
        choices = scene_spec["choices"]
        if not isinstance(choices, list):
            raise TypeError("scene_spec['choices'] must be a list")
        choices_set = set()
        for idx, choice in enumerate(choices):
            if not isinstance(choice, str):
                raise TypeError(f"scene_spec['choices'][{idx}] must be a str")
            if choice not in _ACTION_TYPES:
                raise ValueError(f"scene_spec['choices'][{idx}] is invalid: {choice!r}")
            if choice in choices_set:
                raise ValueError(f"scene_spec['choices'] contains duplicate action: {choice!r}")
            choices_set.add(choice)

    if "choice_text" in scene_spec:
        choice_text = scene_spec["choice_text"]
        if not isinstance(choice_text, dict):
            raise TypeError("scene_spec['choice_text'] must be a dict")
        for action, label in choice_text.items():
            if not isinstance(action, str):
                raise TypeError("scene_spec['choice_text'] keys must be str")
            if action not in _ACTION_TYPES:
                raise ValueError(f"scene_spec['choice_text'] key is invalid action: {action!r}")
            if not isinstance(label, str):
                raise TypeError(f"scene_spec['choice_text'][{action!r}] must be a str")
            if choices_set is not None and action not in choices_set:
                raise ValueError(
                    f"scene_spec['choice_text'] contains action not in choices: {action!r}"
                )

    for key in ("tags", "thread_ids"):
        if key in scene_spec:
            values = scene_spec[key]
            if not isinstance(values, list):
                raise TypeError(f"scene_spec[{key!r}] must be a list")
            seen: set[str] = set()
            for idx, value in enumerate(values):
                if not isinstance(value, str):
                    raise TypeError(f"scene_spec[{key!r}][{idx}] must be a str")
                if not value:
                    raise ValueError(f"scene_spec[{key!r}][{idx}] must be non-empty")
                if value in seen:
                    raise ValueError(f"scene_spec[{key!r}] contains duplicate value: {value!r}")
                seen.add(value)

    if "difficulty" in scene_spec:
        difficulty = scene_spec["difficulty"]
        if isinstance(difficulty, bool) or not isinstance(difficulty, (int, float)):
            raise TypeError("scene_spec['difficulty'] must be a float")
        difficulty_f = float(difficulty)
        if not math.isfinite(difficulty_f):
            raise ValueError("scene_spec['difficulty'] must be finite")
        if difficulty_f < 0.0:
            raise ValueError("scene_spec['difficulty'] must be non-negative")


def validate_observation(observation: Observation) -> None:
    """
    Stub validator for 'Observation' payloads crossing module boundaries.

    Args:
        observation: Player-behavior observation payload to validate.

    Returns:
        None.

    Interaction:
        implementation should enforce observation schema constraints
        before 'PlayerModel' consumes the payload.
    """
    if not isinstance(observation, dict):
        raise TypeError("observation must be a dict")

    for key in observation:
        if key not in _OBSERVATION_KEYS:
            raise ValueError(f"observation contains unknown key: {key!r}")

    if "choice" in observation:
        choice = observation["choice"]
        if not isinstance(choice, str):
            raise TypeError("observation['choice'] must be a str")
        if choice not in _ACTION_TYPES:
            raise ValueError(f"observation['choice'] is invalid: {choice!r}")

    if "choice_tags" in observation:
        choice_tags = observation["choice_tags"]
        if not isinstance(choice_tags, list):
            raise TypeError("observation['choice_tags'] must be a list")
        for idx, tag in enumerate(choice_tags):
            if not isinstance(tag, str):
                raise TypeError(f"observation['choice_tags'][{idx}] must be a str")
            if not tag:
                raise ValueError(f"observation['choice_tags'][{idx}] must be non-empty")

    for key in ("risk_level", "social_intent", "exploration_intent", "aggression_signal"):
        if key in observation:
            value = observation[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"observation[{key!r}] must be a float")
            value_f = float(value)
            if not math.isfinite(value_f):
                raise ValueError(f"observation[{key!r}] must be finite")
            if value_f < 0.0 or value_f > 1.0:
                raise ValueError(f"observation[{key!r}] must be in [0.0, 1.0]")

    for key in ("success", "failure"):
        if key in observation and not isinstance(observation[key], bool):
            raise TypeError(f"observation[{key!r}] must be a bool")

    if "metadata" in observation and not isinstance(observation["metadata"], dict):
        raise TypeError("observation['metadata'] must be a dict")
''

def validate_outcome(outcome: Outcome) -> None:
    """
    Stub validator for 'Outcome' payloads crossing module boundaries.

    Args:
        outcome: Resolver-produced delta payload to validate.

    Returns:
        None.

    Interaction:
        Future implementation should enforce delta-only semantics and validate
        keys/types before 'GameState' or DDA systems consume the payload.
    """
    if not isinstance(outcome, dict):
        raise TypeError("outcome must be a dict")

    for key in outcome:
        if key not in _OUTCOME_KEYS:
            raise ValueError(f"outcome contains unknown key: {key!r}")

    if "player" in outcome:
        player = outcome["player"]
        if not isinstance(player, dict):
            raise TypeError("outcome['player'] must be a dict")
        for k in player:
            if not isinstance(k, str):
                raise TypeError("outcome['player'] keys must be str")
            if not k:
                raise ValueError("outcome['player'] keys must be non-empty")

    inventory_add_set: set[str] | None = None
    if "inventory_add" in outcome:
        inventory_add = outcome["inventory_add"]
        if not isinstance(inventory_add, list):
            raise TypeError("outcome['inventory_add'] must be a list")
        inventory_add_set = set()
        for idx, item in enumerate(inventory_add):
            if not isinstance(item, str):
                raise TypeError(f"outcome['inventory_add'][{idx}] must be a str")
            if not item:
                raise ValueError(f"outcome['inventory_add'][{idx}] must be non-empty")
            if item in inventory_add_set:
                raise ValueError(f"outcome['inventory_add'] contains duplicate item: {item!r}")
            inventory_add_set.add(item)

    if "inventory_remove" in outcome:
        inventory_remove = outcome["inventory_remove"]
        if not isinstance(inventory_remove, list):
            raise TypeError("outcome['inventory_remove'] must be a list")
        seen_remove: set[str] = set()
        for idx, item in enumerate(inventory_remove):
            if not isinstance(item, str):
                raise TypeError(f"outcome['inventory_remove'][{idx}] must be a str")
            if not item:
                raise ValueError(f"outcome['inventory_remove'][{idx}] must be non-empty")
            if item in seen_remove:
                raise ValueError(f"outcome['inventory_remove'] contains duplicate item: {item!r}")
            if inventory_add_set is not None and item in inventory_add_set:
                raise ValueError(
                    f"outcome cannot add and remove the same inventory item: {item!r}"
                )
            seen_remove.add(item)

    if "flags" in outcome:
        flags = outcome["flags"]
        if not isinstance(flags, dict):
            raise TypeError("outcome['flags'] must be a dict")
        for flag, value in flags.items():
            if not isinstance(flag, str):
                raise TypeError("outcome['flags'] keys must be str")
            if not flag:
                raise ValueError("outcome['flags'] keys must be non-empty")
            if not isinstance(value, bool):
                raise TypeError(f"outcome['flags'][{flag!r}] must be a bool")

    if "relationships" in outcome:
        relationships = outcome["relationships"]
        if not isinstance(relationships, dict):
            raise TypeError("outcome['relationships'] must be a dict")
        for entity_id, delta in relationships.items():
            if not isinstance(entity_id, str):
                raise TypeError("outcome['relationships'] keys must be str")
            if not entity_id:
                raise ValueError("outcome['relationships'] keys must be non-empty")
            if isinstance(delta, bool) or not isinstance(delta, (int, float)):
                raise TypeError(f"outcome['relationships'][{entity_id!r}] must be a float")
            delta_f = float(delta)
            if not math.isfinite(delta_f):
                raise ValueError(f"outcome['relationships'][{entity_id!r}] must be finite")

    for key in ("tension_delta", "difficulty_signal"):
        if key in outcome:
            value = outcome[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"outcome[{key!r}] must be a float")
            value_f = float(value)
            if not math.isfinite(value_f):
                raise ValueError(f"outcome[{key!r}] must be finite")

    for key in ("plot_threads", "events"):
        if key in outcome:
            entries = outcome[key]
            if not isinstance(entries, list):
                raise TypeError(f"outcome[{key!r}] must be a list")
            for idx, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    raise TypeError(f"outcome[{key!r}][{idx}] must be a dict")

    if "world_facts" in outcome:
        world_facts = outcome["world_facts"]
        if not isinstance(world_facts, dict):
            raise TypeError("outcome['world_facts'] must be a dict")
        for fact_key in world_facts:
            if not isinstance(fact_key, str):
                raise TypeError("outcome['world_facts'] keys must be str")
            if not fact_key:
                raise ValueError("outcome['world_facts'] keys must be non-empty")

    if "success" in outcome and not isinstance(outcome["success"], bool):
        raise TypeError("outcome['success'] must be a bool")

    if "metadata" in outcome and not isinstance(outcome["metadata"], dict):
        raise TypeError("outcome['metadata'] must be a dict")


__all__ = [
    "ActionType",
    "BeatType",
    "Observation",
    "Outcome",
    "SceneSpec",
    "validate_observation",
    "validate_outcome",
    "validate_scene_spec",
]
