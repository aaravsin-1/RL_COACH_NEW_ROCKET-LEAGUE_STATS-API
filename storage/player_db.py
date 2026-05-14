from __future__ import annotations
import json, os, logging, time
from models.player_profile import PlayerProfile
from models.live_state import LivePlayerState
from config import PLAYER_DB_PATH, EMA_ALPHA

log = logging.getLogger(__name__)


class PlayerDB:
    def __init__(self):
        self._db: dict[str, PlayerProfile] = {}
        self._load()

    def _load(self):
        if not os.path.exists(PLAYER_DB_PATH): return
        try:
            with open(PLAYER_DB_PATH) as f:
                raw = json.load(f)
            for pid, d in raw.items():
                self._db[pid] = PlayerProfile.from_dict(d)
            log.info(f"Loaded {len(self._db)} opponent profiles.")
        except Exception as e:
            log.error(f"PlayerDB load error: {e}")

    def save(self):
        os.makedirs(os.path.dirname(PLAYER_DB_PATH), exist_ok=True)
        try:
            with open(PLAYER_DB_PATH, "w") as f:
                json.dump({pid: p.to_dict() for pid, p in self._db.items()}, f, indent=2)
        except Exception as e:
            log.error(f"PlayerDB save error: {e}")

    def get(self, pid: str, name: str = "") -> PlayerProfile:
        if pid not in self._db:
            self._db[pid] = PlayerProfile.new(pid, name or pid)
        return self._db[pid]

    def all_as_dicts(self) -> list[dict]:
        return [p.to_dict() for p in sorted(
            self._db.values(), key=lambda p: p.matches_seen, reverse=True)]

    def commit_match(self, live: LivePlayerState):
        p = self.get(live.primary_id, live.name)
        a = EMA_ALPHA
        def ema(old, new): return (1-a)*old + a*new
        p.name                = live.name
        p.aggression_avg      = ema(p.aggression_avg,       live.aggression_score)
        p.efficiency_avg      = ema(p.efficiency_avg,       live.efficiency_score)
        p.risk_avg            = ema(p.risk_avg,             live.risk_score)
        p.boost_efficiency_avg= ema(p.boost_efficiency_avg, live.boost_efficiency)
        m = live.elapsed_minutes()
        p.demo_rate  = ema(p.demo_rate,  live.demos   / m)
        p.shot_rate  = ema(p.shot_rate,  live.shots   / m)
        p.touch_rate = ema(p.touch_rate, live.touches / m)
        p.matches_seen += 1
        p.last_seen     = time.time()
        p.estimated_rank = _rank(p)
        self.save()

    def count(self) -> int:
        return len(self._db)


def _rank(p: PlayerProfile) -> str:
    s = p.efficiency_avg*0.5 + (1-p.risk_avg)*0.3 + min(p.touch_rate/15,1)*0.2
    if s >= 0.75: return "Grand Champ+"
    if s >= 0.60: return "Diamond / Champ"
    if s >= 0.45: return "Platinum / Diamond"
    if s >= 0.30: return "Gold / Platinum"
    return "Bronze / Silver"
