"""Optional GOAP planning interface for NPC action sequencing."""

from __future__ import annotations

from typing import Any


class GOAPPlanner:
    """
    Goal-Oriented Action Planning (GOAP) planner interface.

    Intended behavior (not implemented here):
    - Perform forward search from 'start_facts' toward 'goal_facts'.
    - Evaluate action preconditions/effects to expand valid states.
    - Track cumulative action costs and return a minimal/acceptable plan.

    This planner is optional in the course project and may be used by
    'ai.npc_agent.NPCAgent' to produce believable multi-step NPC behavior.
    """

    def __init__(self) -> None:
        """
        Initialize planner configuration and search parameters.

        Returns:
            None.

        Interaction:
            Future implementation may configure search limits, heuristics, and
            cost weighting for action plans.
        """
        # TODO: Initialize planner search settings and cost heuristics.
        pass

    def plan(
        self,
        start_facts: dict[str, Any],
        goal_facts: dict[str, Any],
        actions: list[dict[str, Any]],
    ) -> list[str]:
        """
        Produce a GOAP action plan using forward search over symbolic facts.

        Args:
            start_facts: Current world/NPC facts at planning start.
            goal_facts: Desired facts the planner is trying to satisfy.
            actions: Available action definitions, each expected to describe
                preconditions, effects, and a cost (or cost components).

        Returns:
            Ordered list of action identifiers representing the selected plan.

        Interaction:
            'NPCAgent' may call this planner after selecting an NPC goal. The
            planner should remain a pure planning component and not mutate
            'GameState' directly.
        """
        pass
