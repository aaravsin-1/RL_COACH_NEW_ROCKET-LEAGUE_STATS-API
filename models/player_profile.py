from __future__ import annotations
import time
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class PlayerProfile:
    primary_id: str
    name:       str

    # EMA averages
    aggression_avg:       float = 0.50
    efficiency_avg:       float = 0.50
    risk_avg:             float = 0.50
    boost_efficiency_avg: float = 0.50
    demo_rate:            float = 0.00
    shot_rate:            float = 0.00
    touch_rate:           float = 0.00

    matches_seen: int   = 0
    last_seen:    float = field(default_factory=time.time)
    estimated_rank: Optional[str] = None

    @property
    def confidence(self) -> str:
        from config import CONFIDENCE_LOW, CONFIDENCE_MED, CONFIDENCE_HIGH
        if self.matches_seen < CONFIDENCE_LOW:  return "none"
        if self.matches_seen < CONFIDENCE_MED:  return "low"
        if self.matches_seen < CONFIDENCE_HIGH: return "medium"
        return "high"

    @property
    def playstyle(self) -> str:
        a, e = self.aggression_avg, self.efficiency_avg
        from config import AGG_HIGH, AGG_LOW
        if a >= AGG_HIGH and e < 0.40:  return "Ball-Chaser"
        if a >= AGG_HIGH and e >= 0.40: return "Aggressive-Efficient"
        if a <= AGG_LOW  and e >= 0.50: return "Calculated-Passive"
        if a <= AGG_LOW  and e < 0.50:  return "Passive"
        return "Balanced"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["playstyle"]  = self.playstyle
        d["confidence"] = self.confidence
        return d

    @classmethod
    def from_dict(cls, d: dict) -> PlayerProfile:
        skip = {"playstyle", "confidence"}
        valid = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in valid and k not in skip})

    @classmethod
    def new(cls, pid: str, name: str) -> PlayerProfile:
        return cls(primary_id=pid, name=name)
