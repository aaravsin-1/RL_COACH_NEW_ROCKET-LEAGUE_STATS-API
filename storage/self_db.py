"""
storage/self_db.py

Fix 4: Counting stats (goals/saves/touches etc) now use true running
average so avg_goals after 2 matches of 2 goals each = 2.0, not 0.875.
Behavioural metrics (aggression/efficiency/risk) keep EMA since
recent match should weigh more than a match 50 games ago.
"""
from __future__ import annotations
import json, os, logging, time
from models.self_profile import SelfProfile
from models.session_record import MatchRecord
from models.live_state import LivePlayerState
from config import SELF_DB_PATH, MATCH_HISTORY_PATH, EMA_ALPHA, SESSION_WINDOW_HOURS

log = logging.getLogger(__name__)


class SelfDB:
    def __init__(self):
        self.profile = SelfProfile()
        self.history: list[MatchRecord] = []
        self._load()

    # ── Persistence ───────────────────────────────────────────────
    def _load(self):
        if os.path.exists(SELF_DB_PATH):
            try:
                with open(SELF_DB_PATH) as f:
                    self.profile = SelfProfile.from_dict(json.load(f))
                log.info(f"Self profile: {self.profile.total_matches} matches.")
            except Exception as e:
                log.error(f"SelfDB load: {e}")

        if os.path.exists(MATCH_HISTORY_PATH):
            try:
                with open(MATCH_HISTORY_PATH) as f:
                    self.history = [MatchRecord.from_dict(d) for d in json.load(f)]
                log.info(f"Match history: {len(self.history)} records.")
            except Exception as e:
                log.error(f"History load: {e}")

    def _save(self):
        os.makedirs("data", exist_ok=True)
        try:
            with open(SELF_DB_PATH, "w") as f:
                json.dump(self.profile.to_dict(), f, indent=2)
            from config import MAX_MATCH_HISTORY
            with open(MATCH_HISTORY_PATH, "w") as f:
                json.dump([r.to_dict() for r in self.history[-MAX_MATCH_HISTORY:]], f, indent=2)
        except Exception as e:
            log.error(f"SelfDB save: {e}")

    # ── Session ───────────────────────────────────────────────────
    def ensure_session(self):
        if self.history:
            last = self.history[-1].timestamp
            if (time.time() - last) > SESSION_WINDOW_HOURS * 3600:
                self.profile.session_matches = 0
                self.profile.session_wins    = 0
                self.profile.session_start   = time.time()

    # ── Commit ────────────────────────────────────────────────────
    def commit_match(self, record: MatchRecord):
        p = self.profile
        α = EMA_ALPHA

        # Number of matches BEFORE this one (for running average)
        n = p.total_matches

        # ── EMA for BEHAVIOURAL metrics ───────────────────────────
        # Recent behaviour should outweigh old, so EMA is correct here.
        def ema(old, new): return (1 - α) * old + α * new

        p.avg_aggression    = ema(p.avg_aggression,    record.aggression)
        p.avg_efficiency    = ema(p.avg_efficiency,    record.efficiency)
        p.avg_risk          = ema(p.avg_risk,          record.risk)
        p.avg_boost_eff     = ema(p.avg_boost_eff,     record.boost_eff)
        p.avg_shot_accuracy = ema(p.avg_shot_accuracy, record.shot_accuracy)

        # ── Running average for COUNTING stats ────────────────────
        # avg after 1 match = match value exactly.
        # avg after N matches = true mean. No decay.
        def run_avg(old, new):
            if n == 0:
                return float(new)
            return (old * n + new) / (n + 1)

        p.avg_goals   = run_avg(p.avg_goals,   record.goals)
        p.avg_saves   = run_avg(p.avg_saves,   record.saves)
        p.avg_touches = run_avg(p.avg_touches, record.touches)
        p.avg_score   = run_avg(p.avg_score,   record.score)

        # ── Win/loss ──────────────────────────────────────────────
        p.total_matches   += 1
        p.session_matches += 1
        if record.won:
            p.total_wins     += 1
            p.session_wins   += 1
            p.current_streak  = max(p.current_streak, 0) + 1
            p.best_win_streak = max(p.best_win_streak, p.current_streak)
        else:
            p.total_losses   += 1
            p.current_streak  = min(p.current_streak, 0) - 1
            p.worst_loss_streak = max(p.worst_loss_streak, abs(p.current_streak))

        p.last_seen = time.time()
        self.history.append(record)
        self._save()
        log.info(
            f"Self committed: {'WIN' if record.won else 'LOSS'} | "
            f"avg_goals={p.avg_goals:.2f} avg_saves={p.avg_saves:.2f} | "
            f"streak={p.streak_label}"
        )

    # ── Queries ───────────────────────────────────────────────────
    def recent(self, n: int = 10) -> list[MatchRecord]:
        return self.history[-n:]

    def session_records(self) -> list[MatchRecord]:
        cutoff = time.time() - SESSION_WINDOW_HOURS * 3600
        return [r for r in self.history if r.timestamp >= cutoff]

    def last_match(self) -> MatchRecord | None:
        return self.history[-1] if self.history else None

    def tilt_detected(self) -> bool:
        from config import TILT_EFF_DROP, TILT_WINDOW
        recent = self.recent(TILT_WINDOW)
        if len(recent) < TILT_WINDOW:
            return False
        # Efficiency dropping over last N matches = tilt
        return (recent[0].efficiency - recent[-1].efficiency) > TILT_EFF_DROP
