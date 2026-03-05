"""Utility-based AI Dungeon Master policy for scene/encounter selection."""

from __future__ import annotations

import math
import random
from typing import Any, Mapping

from contracts import BeatType, SceneSpec, validate_scene_spec


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
    return {
        "aggression": _clamp(_safe_float(tv.get("aggression", 0.5), 0.5)),
        "caution": _clamp(_safe_float(tv.get("caution", 0.5), 0.5)),
        "exploration": _clamp(_safe_float(tv.get("exploration", 0.5), 0.5)),
        "social": _clamp(_safe_float(tv.get("social", 0.5), 0.5)),
    }


def _get_difficulty_target(dda: Any) -> float:
    if dda is None:
        return 0.5
    if hasattr(dda, "difficulty_target") and callable(dda.difficulty_target):
        try:
            return _clamp(_safe_float(dda.difficulty_target(), 0.5))
        except Exception:
            return 0.5
    return 0.5


def _get_turn_index(state: Any) -> int:
    try:
        return int(getattr(getattr(state, "narrative"), "turn_index"))
    except Exception:
        return 0


def _get_recent_tags(state: Any) -> list[str]:
    try:
        tags = getattr(getattr(state, "narrative"), "recent_scene_tags")
        return list(tags) if isinstance(tags, list) else []
    except Exception:
        return []


def _get_active_thread_ids(state: Any) -> list[str]:
    try:
        ids = getattr(getattr(state, "narrative"), "active_thread_ids")
        return list(ids) if isinstance(ids, list) else []
    except Exception:
        return []


def _get_location_id(state: Any) -> str | None:
    try:
        loc = getattr(getattr(state, "player"), "location_id")
        return str(loc) if loc else None
    except Exception:
        return None


def _get_flags(state: Any) -> dict[str, bool]:
    try:
        flags = getattr(getattr(state, "player"), "flags")
        if isinstance(flags, dict):
            # ensure bool-ish values
            out: dict[str, bool] = {}
            for k, v in flags.items():
                if isinstance(k, str) and k:
                    out[k] = bool(v)
            return out
    except Exception:
        pass
    return {}


def _get_content_db(state: Any) -> Any | None:
    """
    DMPolicy needs encounters/templates from ContentDB, but your method signature
    doesn't include it.

    This helper tries common wiring patterns so your module works in a group
    project even if teammates attach content differently.
    """
    # Most common: state.content_db
    for attr in ("content_db", "content", "db"):
        try:
            obj = getattr(state, attr)
            if obj is not None:
                return obj
        except Exception:
            pass

    # Alternate: state.world_facts["content_db"]
    try:
        wf = getattr(state, "world_facts")
        if isinstance(wf, dict) and "content_db" in wf:
            return wf["content_db"]
    except Exception:
        pass

    return None


def _list_encounters(content_db: Any) -> list[dict[str, Any]]:
    if content_db is None:
        return []
    if hasattr(content_db, "list_encounters") and callable(content_db.list_encounters):
        try:
            enc = content_db.list_encounters()
            return list(enc) if isinstance(enc, list) else []
        except Exception:
            return []
    return []


def _has_required_flags(required: Mapping[str, Any], flags: dict[str, bool]) -> bool:
    """
    Supports prereq flags like:
      {"met_bandits": true, "has_key": false}
    Interprets non-bool values conservatively.
    """
    for k, v in required.items():
        if not isinstance(k, str) or not k:
            return False
        want = bool(v)
        have = bool(flags.get(k, False))
        if have != want:
            return False
    return True


def _softmax_sample(rng: random.Random, items: list[tuple[dict[str, Any], float]], k: int = 1) -> dict[str, Any]:
    """Sample one item from scored candidates using a stable softmax."""
    # Prevent overflow via max-shift
    scores = [s for _, s in items]
    m = max(scores)
    exps = [math.exp(max(-50.0, min(50.0, s - m))) for s in scores]
    total = sum(exps) or 1.0
    weights = [e / total for e in exps]
    return rng.choices([it for it, _ in items], weights=weights, k=k)[0]


class DMPolicy:
    """
    Utility-based scene selection policy.

    Reads (but never mutates) GameState, PlayerModel, DDA controller, and
    ContentDB to produce a SceneSpec.
    """

    def __init__(self) -> None:
        # Tunable weights for utility scoring
        self.w_trait = 0.45
        self.w_difficulty = 0.35
        self.w_thread = 0.15
        self.w_novelty = 0.25  # penalty weight (subtracted)
        self._rng = random.Random()

    def generate_scene_spec(
        self,
        state: Any,
        player_model: Any,
        dda: Any,
        beat_type: BeatType,
    ) -> SceneSpec:
        turn_index = _get_turn_index(state)
        self._rng.seed(turn_index + 9001)

        traits = _get_trait_vector(player_model)
        diff_target = _get_difficulty_target(dda)

        recent_tags = _get_recent_tags(state)[-10:]  # cap window
        active_threads = set(_get_active_thread_ids(state))
        location_id = _get_location_id(state)
        flags = _get_flags(state)

        content_db = _get_content_db(state)
        encounters = _list_encounters(content_db)

        # --------
        # Filtering
        # --------
        candidates: list[dict[str, Any]] = []
        for e in encounters:
            if not isinstance(e, dict):
                continue

            # Beat matching: allow either "beat_type" or "beat_types"
            bt_ok = False
            bt_single = e.get("beat_type")
            bt_list = e.get("beat_types")
            if isinstance(bt_single, str):
                bt_ok = (bt_single == beat_type)
            elif isinstance(bt_list, list):
                bt_ok = any(isinstance(x, str) and x == beat_type for x in bt_list)
            else:
                # If encounter doesn't specify, treat as compatible (lenient).
                bt_ok = True

            if not bt_ok:
                continue

            # Location constraint (optional)
            e_loc = e.get("location_id")
            if isinstance(e_loc, str) and e_loc and location_id and e_loc != location_id:
                continue

            # Prereq flags (optional)
            prereq = e.get("prereq_flags")
            if isinstance(prereq, dict):
                if not _has_required_flags(prereq, flags):
                    continue

            candidates.append(e)

        # If no candidates available, return safe fallback SceneSpec
        if not candidates:
            scene_spec: SceneSpec = {
                "scene_id": f"fallback_{beat_type}_{turn_index}",
                "beat_type": beat_type,
                "template_id": "fallback",
                "template_group": "fallback",
                "text_vars": {
                    "beat": beat_type,
                    "location": location_id or "unknown",
                },
                "choices": ["explore", "talk", "wait", "retreat"],
                "choice_text": {
                    "explore": "Look around",
                    "talk": "Call out",
                    "wait": "Wait and listen",
                    "retreat": "Leave carefully",
                },
                "tags": [beat_type, "fallback"],
                "location_id": location_id or "start",
                "difficulty": float(diff_target),
                "thread_ids": list(active_threads),
                "metadata": {"reason": "no_candidates"},
            }
            validate_scene_spec(scene_spec)
            return scene_spec

        # --------
        # Scoring
        # --------
        def trait_match(enc: dict[str, Any]) -> float:
            """
            Supports optional 'trait_affinity' mapping:
              {"aggression": 1.0, "caution": -0.3, ...}
            Positive means the encounter is better for that trait; negative worse.
            """
            aff = enc.get("trait_affinity")
            if not isinstance(aff, dict):
                return 0.5  # neutral
            s = 0.0
            w = 0.0
            for key in ("aggression", "caution", "exploration", "social"):
                if key in aff:
                    a = _safe_float(aff.get(key), 0.0)
                    t = traits[key]
                    # map t in [0,1] to centered [-1,1] for synergy
                    centered = (2.0 * t) - 1.0
                    s += a * centered
                    w += abs(a)
            if w <= 1e-9:
                return 0.5
            # normalize to [0,1]
            return _clamp(0.5 + 0.5 * (s / w))

        def difficulty_match(enc: dict[str, Any]) -> float:
            d = enc.get("difficulty", diff_target)
            d = _clamp(_safe_float(d, diff_target))
            # score 1.0 if equal, falls off linearly with distance
            return _clamp(1.0 - abs(d - diff_target))

        def thread_relevance(enc: dict[str, Any]) -> float:
            tids = enc.get("thread_ids")
            if not isinstance(tids, list) or not tids:
                return 0.0
            hit = 0
            total = 0
            for x in tids:
                if isinstance(x, str) and x:
                    total += 1
                    if x in active_threads:
                        hit += 1
            if total == 0:
                return 0.0
            return _clamp(hit / total)

        def novelty_penalty(enc: dict[str, Any]) -> float:
            tags = enc.get("tags")
            if not isinstance(tags, list) or not tags or not recent_tags:
                return 0.0
            # Penalize overlap with recent tags (more overlap => more penalty)
            seen = set(t for t in recent_tags if isinstance(t, str))
            overlap = 0
            total = 0
            for t in tags:
                if isinstance(t, str) and t:
                    total += 1
                    if t in seen:
                        overlap += 1
            if total == 0:
                return 0.0
            return _clamp(overlap / total)

        scored: list[tuple[dict[str, Any], float]] = []
        for e in candidates:
            t = trait_match(e)
            d = difficulty_match(e)
            r = thread_relevance(e)
            n = novelty_penalty(e)

            utility = (
                self.w_trait * t
                + self.w_difficulty * d
                + self.w_thread * r
                - self.w_novelty * n
            )

            # Small tie-break jitter
            utility += self._rng.uniform(-0.01, 0.01)
            scored.append((e, utility))

        scored.sort(key=lambda kv: kv[1], reverse=True)

        # Sample from top few (softmax) to reduce repetition while preferring best
        top = scored[: min(5, len(scored))]
        chosen = _softmax_sample(self._rng, top)

        # --------
        # Build SceneSpec
        # --------
        enc_id = chosen.get("id") or chosen.get("scene_id") or f"enc_{turn_index}"
        template_id = chosen.get("template_id") or chosen.get("template") or "fallback"
        template_group = chosen.get("template_group") or chosen.get("group") or "default"
        tags = chosen.get("tags") if isinstance(chosen.get("tags"), list) else []
        tags_clean = [t for t in tags if isinstance(t, str) and t]
        if beat_type not in tags_clean:
            tags_clean = [beat_type] + tags_clean

        # Choices: allow encounter to define, else reasonable defaults per beat
        raw_choices = chosen.get("choices")
        if isinstance(raw_choices, list) and all(isinstance(x, str) for x in raw_choices):
            choices = raw_choices  # validated later by contracts.validate_scene_spec
        else:
            if beat_type == "combat":
                choices = ["attack", "defend", "use_item", "retreat"]
            elif beat_type == "social":
                choices = ["talk", "investigate", "wait", "retreat"]
            elif beat_type == "mystery":
                choices = ["investigate", "explore", "talk", "wait"]
            elif beat_type == "recovery":
                choices = ["use_item", "wait", "explore", "talk"]
            else:
                choices = ["explore", "investigate", "talk", "retreat"]

        choice_text = chosen.get("choice_text") if isinstance(chosen.get("choice_text"), dict) else {}
        # Ensure every choice has some label
        for c in choices:
            if c not in choice_text:
                choice_text[c] = c.replace("_", " ").title()

        thread_ids = chosen.get("thread_ids")
        if not (isinstance(thread_ids, list) and all(isinstance(x, str) for x in thread_ids)):
            thread_ids = list(active_threads)

        difficulty = chosen.get("difficulty", diff_target)
        difficulty = _clamp(_safe_float(difficulty, diff_target))

        text_vars = chosen.get("text_vars") if isinstance(chosen.get("text_vars"), dict) else {}
        # Add some safe contextual vars
        text_vars.setdefault("location_id", location_id or "start")
        text_vars.setdefault("beat_type", beat_type)
        text_vars.setdefault("encounter_id", str(enc_id))

        scene_spec: SceneSpec = {
            "scene_id": str(enc_id),
            "beat_type": beat_type,
            "template_id": str(template_id),
            "template_group": str(template_group),
            "text_vars": text_vars,
            "choices": choices,  # must be valid ActionType strings
            "choice_text": choice_text,
            "tags": tags_clean,
            "location_id": location_id or "start",
            "difficulty": float(difficulty),
            "thread_ids": thread_ids,
            "metadata": {
                "utility_top": [{"id": (x[0].get("id") or x[0].get("scene_id")), "u": x[1]} for x in top],
                "difficulty_target": diff_target,
            },
        }

        validate_scene_spec(scene_spec)
        return scene_spec