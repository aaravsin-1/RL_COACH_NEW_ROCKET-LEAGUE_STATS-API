from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from models.live_state import LivePlayerState
from models.player_profile import PlayerProfile


@dataclass
class PlayerInsight:
    primary_id: str
    name:       str
    team_num:   int
    # live
    live_aggression: float = 0.5
    live_efficiency: float = 0.5
    live_risk:       float = 0.5
    live_boost_eff:  float = 0.5
    # history
    hist_aggression: float = 0.5
    hist_efficiency: float = 0.5
    playstyle:       str   = "Unknown"
    estimated_rank:  str   = "Unknown"
    confidence:      str   = "none"
    matches_seen:    int   = 0
    # deviation
    more_aggressive: bool  = False
    more_passive:    bool  = False
    # stats
    goals:   int = 0
    shots:   int = 0
    saves:   int = 0
    demos:   int = 0
    assists: int = 0
    touches: int = 0
    score:   int = 0
    # tips
    tips: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "primary_id": self.primary_id,
            "name":       self.name,
            "team_num":   self.team_num,
            "live": {
                "aggression": round(self.live_aggression, 3),
                "efficiency": round(self.live_efficiency, 3),
                "risk":       round(self.live_risk,       3),
                "boost_eff":  round(self.live_boost_eff,  3),
            },
            "history": {
                "aggression": round(self.hist_aggression, 3),
                "efficiency": round(self.hist_efficiency, 3),
                "playstyle":  self.playstyle,
                "rank":       self.estimated_rank,
                "confidence": self.confidence,
                "matches":    self.matches_seen,
            },
            "deviation": {
                "aggressive": self.more_aggressive,
                "passive":    self.more_passive,
            },
            "stats": {
                "goals":   self.goals,
                "shots":   self.shots,
                "saves":   self.saves,
                "demos":   self.demos,
                "assists": self.assists,
                "touches": self.touches,
                "score":   self.score,
            },
            "tips": self.tips,
        }


class AnalysisEngine:
    def build(self, live: LivePlayerState,
              profile: Optional[PlayerProfile]) -> PlayerInsight:
        ins = PlayerInsight(
            primary_id       = live.primary_id,
            name             = live.name,
            team_num         = live.team_num,
            live_aggression  = live.aggression_score,
            live_efficiency  = live.efficiency_score,
            live_risk        = live.risk_score,
            live_boost_eff   = live.boost_efficiency,
            goals   = live.goals,   shots   = live.shots,
            saves   = live.saves,   demos   = live.demos,
            assists = live.assists, touches = live.touches,
            score   = live.score,
        )
        if profile:
            ins.hist_aggression = profile.aggression_avg
            ins.hist_efficiency = profile.efficiency_avg
            ins.playstyle       = profile.playstyle
            ins.estimated_rank  = profile.estimated_rank or "Unknown"
            ins.confidence      = profile.confidence
            ins.matches_seen    = profile.matches_seen
            if profile.confidence in ("medium", "high"):
                d = live.aggression_score - profile.aggression_avg
                ins.more_aggressive = d >  0.20
                ins.more_passive    = d < -0.20
        return ins
