"""Authoritative game state models and mutation boundary contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from contracts import Outcome, validate_outcome


@dataclass(slots=True)
class PlayerState:
    """
    Mutable player-facing world state owned by 'GameState'.

    This dataclass stores directly persistent player information that can change
    across turns, such as location, health/resources, inventory, and
    relationship values. Relationship tracking is represented here so resolver
    outcomes can describe deltas and 'GameState.apply_outcome(...)' can apply
    them in one place.
    """

    name: str = "Adventurer"
    location_id: str = "start"
    health: int = 100
    inventory: list[str] = field(default_factory=list)
    relationships: dict[str, float] = field(default_factory=dict)
    flags: dict[str, bool] = field(default_factory=dict)


@dataclass(slots=True)
class NarrativeState:
    """
    Tracks narrative pacing and memory metadata for the AI Dungeon Master.

    This model captures turn count, tension, recent beat/tag history, and other
    pacing signals used by 'DMBT' and 'DMPolicy'. It is part of the world memory
    in the broad sense because it records what has recently happened so the
    system can avoid repetition and manage story escalation.
    """

    turn_index: int = 0
    tension: float = 0.0
    recent_scene_tags: list[str] = field(default_factory=list)
    beat_history: list[str] = field(default_factory=list)
    active_thread_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PlotThread:
    """
    Represents a narrative thread that can progress over multiple turns.

    Plot threads are separate objects so the system can track progression
    independent of scene rendering. Resolver outcomes should describe changes to
    thread state (progress, status, priority), and 'GameState.apply_outcome(...)'
    is responsible for applying those updates consistently.
    """

    thread_id: str = ""
    title: str = ""
    status: str = "inactive"
    progress: float = 0.0
    priority: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GameState:
    """
    Authoritative mutable world state for the Adaptive AI Dungeon Master.

    'GameState' owns the only writeable representation of world facts. Other
    modules may inspect it, but they must not mutate it directly. This strict
    boundary supports reproducibility and clearer AI/data contracts:

    - 'DMPolicy' reads world state to score scene candidates but cannot change it.
    - 'PlayerModel' reads observations and internal model state only.
    - 'Resolver' computes deltas and observations without mutating 'GameState'.
    - 'GameState.apply_outcome(...)' applies mutations to player state, world
      memory, plot thread progression, relationships, and tension.

    Fields in this skeleton intentionally remain generic so the course project
    can evolve its schema without breaking module boundaries.
    """

    player: PlayerState = field(default_factory=PlayerState)
    narrative: NarrativeState = field(default_factory=NarrativeState)
    plot_threads: dict[str, PlotThread] = field(default_factory=dict)
    world_facts: dict[str, Any] = field(default_factory=dict)
    event_history: list[dict[str, Any]] = field(default_factory=list)
    visited_locations: list[str] = field(default_factory=list)

    def push_scene_tags(self, tags: list[str]) -> None:
        """
        Record scene tags in narrative memory for pacing and novelty tracking.

        Args:
            tags: Ordered list of semantic tags (for example 'combat',
                'mystery', 'social', 'travel') associated with the rendered
                scene.

        Returns:
            None.

        Interaction:
            Intended to be called after a scene is selected/rendered so
            'NarrativeState.recent_scene_tags' can inform 'DMBT' pacing and
            'DMPolicy' novelty penalties in later turns.
        """
        pass

    def push_event(self, event: dict[str, Any]) -> None:
        """
        Append an event record to world memory.

        Args:
            event: Structured event payload describing something that occurred in
                the fiction or system pipeline (scene chosen, action taken,
                significant outcome, thread milestone, etc.).

        Returns:
            None.

        Interaction:
            Events form a lightweight world memory/log summary inside the game
            state and may later support plot thread progression checks, recall,
            and narrative callbacks.
        """
        pass

    def apply_outcome(self, outcome: Outcome) -> None:
        """
        Apply a resolver-produced delta payload to the authoritative world state.

        Args:
            outcome: State delta dictionary produced by 'game.resolver'
                containing only changes to apply, not direct object references.
                Typical keys may include:
                'player', 'inventory', 'flags', 'relationships', 'tension_delta',
                'plot_threads', 'world_facts', and 'events'.

        Returns:
            None.

        Interaction:
            This is the mutation boundary for the project. It is responsible for
            applying tension updates, relationship tracking deltas, plot thread
            progression, and other world-state changes while preserving the rule
            that external modules never mutate 'GameState' directly.
        """
        validate_outcome(outcome)
        # TODO: Apply validated outcome deltas to the authoritative world state.
        pass
