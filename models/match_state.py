from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TeamState:
    team_num: int
    name:     str  = ""
    score:    int  = 0
    color:    str  = "0060FF"


@dataclass
class MatchState:
    guid:         Optional[str] = None
    arena:        str  = ""
    time_seconds: int  = 300
    overtime:     bool = False
    has_winner:   bool = False
    winner:       str  = ""
    in_replay:    bool = False
    active:       bool = False
    teams:        list = field(default_factory=list)
    created_at:   float = field(default_factory=time.time)

    def update_from_game(self, g: dict):
        self.time_seconds = g.get("TimeSeconds", self.time_seconds)
        self.overtime     = g.get("bOvertime",   self.overtime)
        self.has_winner   = g.get("bHasWinner",  self.has_winner)
        self.winner       = g.get("Winner",      self.winner)
        self.in_replay    = g.get("bReplay",     self.in_replay)
        self.arena        = g.get("Arena",       self.arena)
        self.teams = [
            TeamState(
                team_num = t.get("TeamNum", i),
                name     = t.get("Name", f"Team {i}"),
                score    = t.get("Score", 0),
                color    = t.get("ColorPrimary", "0060FF" if i == 0 else "FF6000"),
            )
            for i, t in enumerate(g.get("Teams", []))
        ]

    def to_dict(self) -> dict:
        return {
            "guid":         self.guid,
            "arena":        self.arena,
            "time_seconds": self.time_seconds,
            "overtime":     self.overtime,
            "has_winner":   self.has_winner,
            "winner":       self.winner,
            "in_replay":    self.in_replay,
            "active":       self.active,
            "teams": [
                {"team_num": t.team_num, "name": t.name,
                 "score": t.score, "color": t.color}
                for t in self.teams
            ],
        }
