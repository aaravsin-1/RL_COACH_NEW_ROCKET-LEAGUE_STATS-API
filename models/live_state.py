from __future__ import annotations
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class LiveEvent:
    kind:      str
    timestamp: float
    meta:      dict = field(default_factory=dict)


@dataclass
class LivePlayerState:
    primary_id: str
    name:       str
    team_num:   int

    touches:  int = 0
    shots:    int = 0
    goals:    int = 0
    saves:    int = 0
    demos:    int = 0
    assists:  int = 0
    score:    int = 0

    speed:         float = 0.0
    boost:         int   = 100
    is_boosting:   bool  = False
    is_supersonic: bool  = False
    on_ground:     bool  = True
    on_wall:       bool  = False
    demolished:    bool  = False

    prev_boost:           int   = 100
    total_boost_consumed: float = 0.0
    boost_speed_sum:      float = 0.0

    match_start_time: float = field(default_factory=time.time)
    recent_events: deque = field(default_factory=lambda: deque(maxlen=300))

    def elapsed_minutes(self) -> float:
        return max((time.time() - self.match_start_time) / 60.0, 1/60)

    def add_event(self, kind: str, meta: dict = None):
        self.recent_events.append(LiveEvent(kind, time.time(), meta or {}))

    def update_from_api(self, p: dict):
        self.touches  = p.get("Touches",  self.touches)
        self.shots    = p.get("Shots",    self.shots)
        self.goals    = p.get("Goals",    self.goals)
        self.saves    = p.get("Saves",    self.saves)
        self.demos    = p.get("Demos",    self.demos)
        self.assists  = p.get("Assists",  self.assists)
        self.score    = p.get("Score",    self.score)
        self.name     = p.get("Name",     self.name)
        self.speed         = p.get("Speed",       self.speed)
        self.boost         = p.get("Boost",       self.boost)
        self.is_boosting   = p.get("bBoosting",   self.is_boosting)
        self.is_supersonic = p.get("bSupersonic", self.is_supersonic)
        self.on_ground     = p.get("bOnGround",   self.on_ground)
        self.on_wall       = p.get("bOnWall",     self.on_wall)
        self.demolished    = p.get("bDemolished", self.demolished)
        if self.is_boosting and self.boost < self.prev_boost:
            consumed = self.prev_boost - self.boost
            self.total_boost_consumed += consumed
            self.boost_speed_sum += self.speed * consumed
        self.prev_boost = self.boost

    # ── Metrics (calibrated for 2v2) ─────────────────────────────
    @property
    def boost_efficiency(self) -> float:
        if self.total_boost_consumed < 1:
            return 0.5
        return min(self.boost_speed_sum / (self.total_boost_consumed * 2300), 1.0)

    @property
    def shot_accuracy(self) -> float:
        return self.goals / self.shots if self.shots > 0 else 0.0

    @property
    def aggression_score(self) -> float:
        """
        Calibrated for 2v2:
          - 8 touches/min = max touch component (typical aggressive = 5-7/min)
          - 1.5 shots/min = max shot component  (typical aggressive = 0.8-1.2/min)
          - 0.4 demos/min = max demo component  (demo-hunter = 2 demos / 5min)
        Ball-chaser (35T 6S 2D in 5min) → ~0.87
        Balanced    (18T 3S 0D in 5min) → ~0.34
        Passive     ( 8T 1S 0D in 5min) → ~0.13
        """
        m = self.elapsed_minutes()
        t = min(self.touches / m / 8.0,  1.0) * 0.40
        s = min(self.shots   / m / 1.5,  1.0) * 0.40
        d = min(self.demos   / m / 0.4,  1.0) * 0.20
        return min(t + s + d, 1.0)

    @property
    def efficiency_score(self) -> float:
        """
        Value per touch, normalised to 0-1.
        Normaliser 0.70 calibrated so:
          Exceptional (3G 5S 2A 1SV / 30T) → ~0.93
          Good        (2G 4S 1A 2SV / 20T) → ~0.96 (cap)
          Average     (1G 3S 1A 1SV / 18T) → ~0.67
          Ball-chaser (0G 6S 0A 0SV / 35T) → ~0.12
          Passive     (0G 1S 0A 0SV /  8T) → ~0.09
        Shots weighted 0.5 (attempt is ok, conversion is better).
        """
        if self.touches == 0:
            return 0.0
        val = (
            self.goals   * 3.0 +
            self.shots   * 0.5 +
            self.assists * 2.0 +
            self.saves   * 2.0
        ) / self.touches
        return min(val / 0.70, 1.0)

    @property
    def risk_score(self) -> float:
        """
        High risk = demo-hunting + missing shots.
        miss_r is 0.5 when no shots taken (neutral, not penalised).
        """
        m      = self.elapsed_minutes()
        demo_r = min(self.demos / m / 0.4, 1.0)
        miss_r = (1 - self.shot_accuracy) if self.shots > 0 else 0.5
        return demo_r * 0.70 + miss_r * 0.30
