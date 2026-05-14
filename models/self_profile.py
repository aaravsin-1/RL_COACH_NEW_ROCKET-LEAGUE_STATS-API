from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SelfProfile:
    name: str = "dogmiv"

    # All-time
    total_matches: int   = 0
    total_wins:    int   = 0
    total_losses:  int   = 0

    # Streak (positive=win, negative=loss)
    current_streak:    int = 0
    best_win_streak:   int = 0
    worst_loss_streak: int = 0

    # EMA averages
    avg_aggression:    float = 0.50
    avg_efficiency:    float = 0.50
    avg_risk:          float = 0.50
    avg_boost_eff:     float = 0.50
    avg_shot_accuracy: float = 0.00
    avg_goals:         float = 0.00
    avg_saves:         float = 0.00
    avg_touches:       float = 0.00
    avg_score:         float = 0.00

    # Session (reset each session)
    session_start:   float = field(default_factory=time.time)
    session_matches: int   = 0
    session_wins:    int   = 0

    first_seen: float = field(default_factory=time.time)
    last_seen:  float = field(default_factory=time.time)

    @property
    def win_rate(self) -> float:
        return self.total_wins / self.total_matches if self.total_matches else 0.0

    @property
    def session_win_rate(self) -> float:
        return self.session_wins / self.session_matches if self.session_matches else 0.0

    @property
    def streak_label(self) -> str:
        s = self.current_streak
        if s == 0: return "–"
        return f"W{s}" if s > 0 else f"L{abs(s)}"

    @property
    def streak_type(self) -> str:
        if self.current_streak > 0: return "win"
        if self.current_streak < 0: return "loss"
        return "none"

    def to_dict(self) -> dict:
        return {
            "name":             self.name,
            "total_matches":    self.total_matches,
            "total_wins":       self.total_wins,
            "total_losses":     self.total_losses,
            "current_streak":   self.current_streak,
            "best_win_streak":  self.best_win_streak,
            "worst_loss_streak":self.worst_loss_streak,
            "avg_aggression":   round(self.avg_aggression,    3),
            "avg_efficiency":   round(self.avg_efficiency,    3),
            "avg_risk":         round(self.avg_risk,          3),
            "avg_boost_eff":    round(self.avg_boost_eff,     3),
            "avg_shot_accuracy":round(self.avg_shot_accuracy, 3),
            "avg_goals":        round(self.avg_goals,         2),
            "avg_saves":        round(self.avg_saves,         2),
            "avg_touches":      round(self.avg_touches,       2),
            "avg_score":        round(self.avg_score,         1),
            "session_start":    self.session_start,
            "session_matches":  self.session_matches,
            "session_wins":     self.session_wins,
            "first_seen":       self.first_seen,
            "last_seen":        self.last_seen,
            # computed
            "win_rate":         round(self.win_rate,         3),
            "session_win_rate": round(self.session_win_rate, 3),
            "streak_label":     self.streak_label,
            "streak_type":      self.streak_type,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SelfProfile:
        skip = {"win_rate","session_win_rate","streak_label","streak_type"}
        p = cls()
        for k, v in d.items():
            if k not in skip and hasattr(p, k):
                setattr(p, k, v)
        return p
