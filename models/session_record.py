from __future__ import annotations
import time
from dataclasses import dataclass, field


@dataclass
class MatchRecord:
    guid:          str
    timestamp:     float = field(default_factory=time.time)
    won:           bool  = False
    team_score:    int   = 0
    opp_score:     int   = 0
    goals:         int   = 0
    shots:         int   = 0
    assists:       int   = 0
    saves:         int   = 0
    demos:         int   = 0
    touches:       int   = 0
    score:         int   = 0
    aggression:    float = 0.5
    efficiency:    float = 0.5
    risk:          float = 0.5
    boost_eff:     float = 0.5
    shot_accuracy: float = 0.0
    duration_secs: int   = 300
    arena:         str   = ""

    # Post-match analysis
    moments:    list = field(default_factory=list)
    strengths:  list = field(default_factory=list)
    weaknesses: list = field(default_factory=list)
    drills:     list = field(default_factory=list)
    motivator:  str  = ""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, d: dict) -> MatchRecord:
        r = cls(guid=d.get("guid",""))
        for k, v in d.items():
            if hasattr(r, k):
                setattr(r, k, v)
        return r
