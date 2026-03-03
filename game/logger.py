"""Structured runtime logging interface for JSON Lines turn records."""

from __future__ import annotations

from typing import Any, cast

from contracts import (
    Observation,
    Outcome,
    SceneSpec,
    validate_observation,
    validate_outcome,
    validate_scene_spec,
)


class RunLogger:
    """
    Structured run logger for analytics, debugging, and reproducibility.

    Intended output format:
    - JSON Lines ('.jsonl'): one JSON object per turn.

    Required fields per turn record (recommended contract):
    - 'turn_index'
    - 'timestamp' (or monotonic sequence metadata)
    - 'beat_type'
    - 'scene_spec'
    - 'rendered_scene' (optional but useful)
    - 'choice'
    - 'outcome'
    - 'observation'
    - 'player_traits'
    - 'difficulty_target'
    - 'state_summary'

    The logger is intentionally separate from 'GameState' so logging side
    effects do not pollute core simulation state.
    """

    def __init__(self, path: str) -> None:
        """
        Prepare a logger that will write JSONL records to 'path'.

        Args:
            path: Output file path for the run log (for example
                'logs/run.jsonl').

        Returns:
            None.

        Interaction:
            The main loop should create one 'RunLogger' per run, call
            'log_turn(...)' once per turn, and call 'close()' during shutdown.
        """
        self.path = path
        # TODO: Open file handle lazily or eagerly and initialize JSONL writer.

    def log_turn(self, record: dict[str, Any]) -> None:
        """
        Write a single structured turn record.

        Args:
            record: JSON-serializable dictionary containing the required turn
                fields and any additional debugging metadata.

        Returns:
            None.

        Interaction:
            Called after each full turn pipeline completes so the record captures
            beat selection, scene generation, player action, resolver outputs,
            and controller/model snapshots.
        """
        if "scene_spec" in record:
            validate_scene_spec(cast(SceneSpec, record["scene_spec"]))
        if "observation" in record:
            validate_observation(cast(Observation, record["observation"]))
        if "outcome" in record:
            validate_outcome(cast(Outcome, record["outcome"]))
        # TODO: Serialize 'record' as one JSON object line in the run log file.
        pass

    def close(self) -> None:
        """
        Close any underlying file resources used by the logger.

        Returns:
            None.

        Interaction:
            Should be called exactly once during graceful shutdown after the last
            turn has been logged.
        """
        pass
