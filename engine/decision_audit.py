"""
engine/decision_audit.py

Fix 3: One touch credited/blamed per goal (no more duplicates).
Fix 3: Time shown as time-remaining directly, no hardcoded 300.
Fix 2: Touches during replays are not recorded (caller guards this).
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from config import AUDIT_WINDOW_SECS


@dataclass
class TouchRecord:
    timestamp:     float
    time_in_match: int     # seconds REMAINING when touch happened
    post_speed:    float = 0.0
    outcome:       str   = "neutral"   # "goal_for" | "goal_against" | "neutral"


class DecisionAuditor:
    def __init__(self):
        self._touches:            list[TouchRecord] = []
        self._goal_for_times:     list[float]       = []
        self._goal_against_times: list[float]       = []

    def reset(self):
        self.__init__()

    def record_touch(self, time_in_match: int, post_speed: float = 0.0):
        self._touches.append(TouchRecord(
            timestamp     = time.time(),
            time_in_match = time_in_match,
            post_speed    = post_speed,
        ))

    def record_goal_for(self):
        self._goal_for_times.append(time.time())

    def record_goal_against(self):
        self._goal_against_times.append(time.time())

    def finalise(self) -> list[dict]:
        """
        For each goal, find the SINGLE most recent touch within
        AUDIT_WINDOW_SECS. Credit or blame that touch only.
        One touch per goal — no duplicates.
        """
        # Process goals-against first (higher priority — most actionable)
        for gt in self._goal_against_times:
            candidates = [
                t for t in self._touches
                if 0 <= (gt - t.timestamp) <= AUDIT_WINDOW_SECS
                and t.outcome == "neutral"
            ]
            if candidates:
                # Blame the most recent touch before this goal
                blamed = max(candidates, key=lambda t: t.timestamp)
                blamed.outcome = "goal_against"

        # Process goals-for
        for gt in self._goal_for_times:
            candidates = [
                t for t in self._touches
                if 0 <= (gt - t.timestamp) <= AUDIT_WINDOW_SECS
                and t.outcome == "neutral"
            ]
            if candidates:
                credited = max(candidates, key=lambda t: t.timestamp)
                credited.outcome = "goal_for"

        moments = []

        # Bad touches (overcommits) — up to 3
        for t in [x for x in self._touches if x.outcome == "goal_against"][:3]:
            mins = t.time_in_match // 60
            secs = t.time_in_match % 60
            moments.append({
                "type":        "overcommit",
                "icon":        "⚠",
                "time":        f"{mins}:{secs:02d}",
                "description": (
                    f"Your touch at {mins}:{secs:02d} remaining led to a "
                    f"conceded goal within {AUDIT_WINDOW_SECS:.0f}s — possible overcommit."
                ),
                "severity": "bad",
            })

        # Good touches — up to 3
        for t in [x for x in self._touches if x.outcome == "goal_for"][:3]:
            mins = t.time_in_match // 60
            secs = t.time_in_match % 60
            moments.append({
                "type":        "good_read",
                "icon":        "✓",
                "time":        f"{mins}:{secs:02d}",
                "description": (
                    f"Your touch at {mins}:{secs:02d} remaining contributed to a "
                    f"goal within {AUDIT_WINDOW_SECS:.0f}s — good read."
                ),
                "severity": "good",
            })

        # Pattern summary
        total      = len(self._touches)
        bad_count  = sum(1 for t in self._touches if t.outcome == "goal_against")
        good_count = sum(1 for t in self._touches if t.outcome == "goal_for")

        if total > 0:
            bad_rate = bad_count / total
            if bad_rate > 0.15:
                moments.append({
                    "type":        "pattern",
                    "icon":        "📊",
                    "time":        "–",
                    "description": (
                        f"{bad_rate:.0%} of your touches led to conceded goals — "
                        f"focus on touch quality over quantity."
                    ),
                    "severity": "warn",
                })
            elif good_count > bad_count:
                moments.append({
                    "type":        "pattern",
                    "icon":        "📊",
                    "time":        "–",
                    "description": (
                        f"More positive touches ({good_count}) than negative ({bad_count}) "
                        f"— decision-making was solid."
                    ),
                    "severity": "good",
                })

        # Sort: bad first, then warn, then good
        order = {"bad": 0, "warn": 1, "good": 2}
        moments.sort(key=lambda m: order.get(m["severity"], 3))
        return moments
