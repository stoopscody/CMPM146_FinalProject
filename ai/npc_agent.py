"""NPC decision interface with optional GOAP-backed planning."""

from __future__ import annotations

from typing import Any


class NPCAgent:
    """
    NPC decision-maker interface for selecting intents or actions.

    Intended responsibilities:
    - Select an NPC goal based on world context and player behavior.
    - Optionally invoke 'GOAPPlanner' to build a plan that satisfies the goal.
    - Return a structured decision artifact for scene generation/resolution.

    This module should read from 'GameState' and 'PlayerModel' but must not
    directly mutate 'GameState'.
    """

    def __init__(self) -> None:
        """
        Initialize NPC decision policy and optional planner references.

        Returns:
            None.

        Interaction:
            Future implementation may attach goal-selection heuristics and a
            'GOAPPlanner' instance for multi-step plan generation.
        """
        # TODO: Initialize NPC goal policy and optional GOAP planner.
        pass

    def decide(self, state: Any, player_model: Any) -> dict[str, Any]:
        """
        Produce an NPC decision artifact for the current turn or scene.

        Args:
            state: Read-only game state context (location, flags, active threads,
                relationships, tension, etc.).
            player_model: Read-only player model used to adapt NPC behavior to
                inferred player traits or archetype.

        Returns:
            Dictionary describing the selected NPC goal, intent, or action plan.

        Interaction:
            A future implementation may first select a goal, then call
            'GOAPPlanner.plan(...)' to produce actions. The resulting artifact can
            be consumed by 'DMPolicy' or 'game.resolver'.
        """
        pass
