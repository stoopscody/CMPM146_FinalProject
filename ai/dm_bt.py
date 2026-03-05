"""Behavior Tree interface for AI Dungeon Master narrative pacing decisions."""

from __future__ import annotations

import random
from typing import Any, Mapping

from contracts import BeatType


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if isinstance(x, bool):
            return default
        return float(x)
    except Exception:
        return default


def _get_trait_vector(player_model: Any) -> dict[str, float]:
    """Try to read PlayerModel.trait_vector() but remain tolerant of stubs."""
    if player_model is None:
        return {"aggression": 0.5, "caution": 0.5, "exploration": 0.5, "social": 0.5}
    tv = None
    if hasattr(player_model, "trait_vector") and callable(player_model.trait_vector):
        try:
            tv = player_model.trait_vector()
        except Exception:
            tv = None
    if not isinstance(tv, Mapping):
        tv = {}
    # Normalize + defaults
    return {
        "aggression": _clamp(_safe_float(tv.get("aggression", 0.5), 0.5)),
        "caution": _clamp(_safe_float(tv.get("caution", 0.5), 0.5)),
        "exploration": _clamp(_safe_float(tv.get("exploration", 0.5), 0.5)),
        "social": _clamp(_safe_float(tv.get("social", 0.5), 0.5)),
    }


def _get_tension(state: Any) -> float:
    """Try to read state.narrative.tension; default to 0.0 if missing."""
    try:
        return _clamp(_safe_float(getattr(getattr(state, "narrative"), "tension"), 0.0))
    except Exception:
        return 0.0


def _get_turn_index(state: Any) -> int:
    try:
        return int(getattr(getattr(state, "narrative"), "turn_index"))
    except Exception:
        return 0


def _get_beat_history(state: Any) -> list[str]:
    try:
        hist = getattr(getattr(state, "narrative"), "beat_history")
        return list(hist) if isinstance(hist, list) else []
    except Exception:
        return []


def _get_active_threads(state: Any) -> int:
    """Count active threads if present."""
    try:
        ids = getattr(getattr(state, "narrative"), "active_thread_ids")
        if isinstance(ids, list):
            return len(ids)
    except Exception:
        pass
    return 0


def _get_difficulty_target(dda: Any) -> float:
    """Try to read dda.difficulty_target(); default to 0.5 if missing."""
    if dda is None:
        return 0.5
    if hasattr(dda, "difficulty_target") and callable(dda.difficulty_target):
        try:
            return _clamp(_safe_float(dda.difficulty_target(), 0.5))
        except Exception:
            return 0.5
    return 0.5


class DMBT:
    """
    Behavior Tree-ish controller for selecting high-level narrative beats.

    This implementation is intentionally lightweight:
    - Computes a score for each BeatType based on tension, repetition,
      player traits, active plot pressure, and DDA guidance.
    - Samples from the best beats to avoid deterministic repetition.
    """

    def __init__(self) -> None:
        # You can tune these weights without changing interfaces.
        self._repeat_penalty = 0.35
        self._same_as_last_penalty = 0.55
        self._rng = random.Random()

    def choose_beat(self, state: Any, player_model: Any, dda: Any) -> BeatType:
        tension = _get_tension(state)
        turn_index = _get_turn_index(state)
        beat_history = _get_beat_history(state)
        active_threads = _get_active_threads(state)
        traits = _get_trait_vector(player_model)
        diff_target = _get_difficulty_target(dda)

        # Seed randomness lightly by turn to keep runs stable-ish if desired.
        # (If your team wants full determinism, replace with fixed seed.)
        self._rng.seed(turn_index + 1337)

        last = beat_history[-1] if beat_history else None
        recent = beat_history[-4:] if len(beat_history) >= 4 else beat_history[:]

        def repeats(b: str) -> int:
            return sum(1 for x in recent if x == b)

        # Base scoring with simple pacing rules:
        # - High tension: prefer recovery/travel/social over combat.
        # - Low tension: allow combat/revelation.
        # - Active threads: nudge mystery/revelation/social a bit.
        scores: dict[BeatType, float] = {
            "exploration": 0.50 + 0.35 * traits["exploration"] + 0.10 * (1.0 - tension),
            "combat": 0.40 + 0.45 * traits["aggression"] + 0.15 * diff_target - 0.65 * tension,
            "social": 0.45 + 0.45 * traits["social"] + 0.10 * (1.0 - diff_target),
            "mystery": 0.40 + 0.25 * traits["exploration"] + 0.10 * active_threads,
            "recovery": 0.25 + 0.95 * tension + 0.20 * traits["caution"],
            "revelation": 0.30 + 0.20 * (1.0 - tension) + 0.15 * active_threads,
            "travel": 0.35 + 0.25 * (1.0 - tension) + 0.10 * traits["exploration"],
        }

        # Repetition avoidance
        for beat in list(scores.keys()):
            r = repeats(beat)
            if r > 0:
                scores[beat] -= self._repeat_penalty * r
            if last == beat:
                scores[beat] -= self._same_as_last_penalty

        # Hard-ish rules:
        # If tension is very high, strongly discourage combat (not forbidden).
        if tension >= 0.85:
            scores["combat"] -= 0.9
        # If tension is very low, discourage recovery.
        if tension <= 0.15:
            scores["recovery"] -= 0.5

        # Add tiny noise for variety
        for beat in scores:
            scores[beat] += self._rng.uniform(-0.05, 0.05)

        # Choose among the top K by score (K=2 or 3), weighted
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        top_k = ranked[:3]

        # Convert to weights (shifted positive)
        min_s = min(s for _, s in top_k)
        weights = [max(0.001, (s - min_s) + 0.01) for _, s in top_k]
        choice = self._rng.choices([b for b, _ in top_k], weights=weights, k=1)[0]
        return choice