"""
session.py
Fix 2: Proper replay handling — BallHit/audit skipped during replays.
GoalReplayStart/End set self.match.in_replay flag.
"""
from __future__ import annotations
import logging
import queue
import time
from typing import Dict, Optional

from config import LOCAL_PLAYER_NAME
from models.live_state import LivePlayerState
from models.match_state import MatchState
from storage.player_db import PlayerDB
from storage.self_db import SelfDB
from engine.analysis_engine import AnalysisEngine
from engine.coaching_engine import CoachingEngine
from engine.decision_audit import DecisionAuditor
from engine.post_match_engine import build_report

log = logging.getLogger(__name__)


class GameSession:
    def __init__(self, player_db: PlayerDB, self_db: SelfDB):
        self.pdb      = player_db
        self.sdb      = self_db
        self.analyser = AnalysisEngine()
        self.coach    = CoachingEngine()
        self.auditor  = DecisionAuditor()

        self.match     = MatchState()
        self.live:      Dict[str, LivePlayerState] = {}
        self.local_pid: Optional[str] = None

        # maxsize=1: overlay always gets the freshest snapshot
        self.state_queue: queue.Queue = queue.Queue(maxsize=1)

        self.last_report  = None
        self.report_ready = False

    # ── Event router ─────────────────────────────────────────────
    def on_event(self, event: str, data: dict):
        {
            "UpdateState":         self._on_update,
            "BallHit":             self._on_ball_hit,
            "GoalScored":          self._on_goal_scored,
            "StatfeedEvent":       self._on_statfeed,
            "CountdownBegin":      self._on_countdown,
            "RoundStarted":        lambda d: self._push(),
            "MatchCreated":        self._on_match_created,
            "MatchInitialized":    lambda d: None,
            "MatchEnded":          self._on_match_ended,
            "MatchDestroyed":      self._on_match_destroyed,
            "ClockUpdatedSeconds": self._on_clock,
            # Fix 2: replay events now properly toggle the flag
            "GoalReplayStart":     self._on_replay_start,
            "GoalReplayEnd":       self._on_replay_end,
            "GoalReplayWillEnd":   lambda d: None,
            "PodiumStart":         lambda d: None,
            "CrossbarHit":         lambda d: None,
            "MatchPaused":         lambda d: None,
            "MatchUnpaused":       lambda d: None,
        }.get(event, lambda d: log.debug(f"Unhandled: {event}"))(data)

    # ── Match lifecycle ───────────────────────────────────────────
    def _on_match_created(self, data: dict):
        self.match            = MatchState()
        self.match.guid       = data.get("MatchGuid")
        self.match.active     = True
        self.live             = {}
        self.local_pid        = None
        self.report_ready     = False
        self.auditor.reset()
        log.info(f"Match created: {self.match.guid}")
        self._push()

    def _on_replay_start(self, data: dict):
        """Fix 2: set replay flag so BallHit/audit are skipped."""
        self.match.in_replay = True
        log.debug("Replay started — pausing audit recording.")

    def _on_replay_end(self, data: dict):
        """Fix 2: clear replay flag."""
        self.match.in_replay = False
        log.debug("Replay ended — resuming audit recording.")

    def _on_countdown(self, data: dict):
        # Do NOT reset match_start_time here — fires on every kickoff.
        self._push()

    def _on_match_ended(self, data: dict):
        winner_team = data.get("WinnerTeamNum", -1)
        log.info(f"Match ended. Winner team: {winner_team}")

        for pid, ls in self.live.items():
            if pid != self.local_pid:
                self.pdb.commit_match(ls)

        if self.local_pid and self.local_pid in self.live:
            ls      = self.live[self.local_pid]
            my_team = ls.team_num
            won     = (my_team == winner_team)

            team_score = opp_score = 0
            for t in self.match.teams:
                if t.team_num == my_team:
                    team_score = t.score
                else:
                    opp_score = t.score

            match_duration = int(time.time() - self.match.created_at)
            session_recs   = self.sdb.session_records()

            report = build_report(
                live            = ls,
                auditor         = self.auditor,
                profile         = self.sdb.profile,
                won             = won,
                team_score      = team_score,
                opp_score       = opp_score,
                arena           = self.match.arena,
                session_records = session_recs,
                match_duration  = match_duration,
            )
            self.sdb.commit_match(report)
            self.last_report  = report
            self.report_ready = True
            log.info(
                f"Report: {'WIN' if won else 'LOSS'} {team_score}-{opp_score} "
                f"dur={match_duration}s | {report.motivator[:60]}"
            )

        self.match.active = False
        self._push()

    def _on_match_destroyed(self, data: dict):
        self.match.active = False
        self.live = {}
        self._push()

    # ── Tick ─────────────────────────────────────────────────────
    def _on_update(self, data: dict):
        if not self.match.active:
            self.match.active = True

        guid = data.get("MatchGuid")
        if guid and not self.match.guid:
            self.match.guid = guid

        self.match.update_from_game(data.get("Game", {}))

        # Detect local player via Game.Target
        game = data.get("Game", {})
        if game.get("bHasTarget") and game.get("Target") and not self.local_pid:
            tname = game["Target"].get("Name", "")
            if tname:
                for pid, ls in self.live.items():
                    if ls.name == tname:
                        self.local_pid = pid
                        log.info(f"Local player via Target: {tname}")
                        break

        for p in data.get("Players", []):
            pid  = p.get("PrimaryId", p.get("Name", "unknown"))
            name = p.get("Name", pid)
            tnum = p.get("TeamNum", 0)

            if pid not in self.live:
                # match_start_time = match created_at, set once, never reset
                self.live[pid] = LivePlayerState(
                    primary_id       = pid,
                    name             = name,
                    team_num         = tnum,
                    match_start_time = self.match.created_at,
                )
                self.pdb.get(pid, name)
                log.info(f"Tracking: {name} ({pid})")
                if name.lower() == LOCAL_PLAYER_NAME.lower():
                    self.local_pid = pid
                    log.info(f"Local player by name: {name}")

            self.live[pid].update_from_api(p)

        self._push()

    # ── Events ───────────────────────────────────────────────────
    def _on_ball_hit(self, data: dict):
        # Fix 2: skip during replays — BallHit fires during goal replays
        # and would contaminate the decision audit with historical touches.
        if self.match.in_replay:
            return

        ball = data.get("Ball", {})
        for p in data.get("Players", []):
            ls = self._by_name(p.get("Name", ""))
            if ls:
                ls.add_event("BallHit", {"post_speed": ball.get("PostHitSpeed", 0)})
                if ls.primary_id == self.local_pid:
                    self.auditor.record_touch(
                        self.match.time_seconds,
                        ball.get("PostHitSpeed", 0),
                    )
        self._push()

    def _on_goal_scored(self, data: dict):
        # GoalScored fires when goal is scored, not during replay
        scorer      = data.get("Scorer", {})
        scorer_ls   = self._by_name(scorer.get("Name", ""))
        scorer_team = scorer.get("TeamNum", -1)

        if scorer_ls:
            scorer_ls.add_event("GoalScored")

        if self.local_pid and self.local_pid in self.live:
            my_team = self.live[self.local_pid].team_num
            if scorer_team == my_team:
                self.auditor.record_goal_for()
            else:
                self.auditor.record_goal_against()

        self._push()

    def _on_statfeed(self, data: dict):
        # Fix 2: skip during replays
        if self.match.in_replay:
            return
        ls = self._by_name(data.get("MainTarget", {}).get("Name", ""))
        if ls:
            ls.add_event(f"Stat:{data.get('EventName','')}")
        self._push()

    def _on_clock(self, data: dict):
        self.match.time_seconds = data.get("TimeSeconds", self.match.time_seconds)
        self.match.overtime     = data.get("bOvertime",   self.match.overtime)

    # ── Snapshot ─────────────────────────────────────────────────
    def snapshot(self) -> dict:
        players_out = []
        for pid, ls in self.live.items():
            profile = self.pdb.get(pid, ls.name)
            insight = self.analyser.build(ls, profile)
            if pid != self.local_pid:
                insight.tips = [t["text"] for t in self.coach.tips(insight)[:3]]
            d = insight.to_dict()
            d["is_self"] = (pid == self.local_pid)
            players_out.append(d)

        players_out.sort(key=lambda p: (p["is_self"], p["team_num"]))

        self_data = None
        if self.local_pid and self.local_pid in self.live:
            ls = self.live[self.local_pid]
            self_data = {
                "name":       ls.name,
                "goals":      ls.goals,
                "shots":      ls.shots,
                "saves":      ls.saves,
                "touches":    ls.touches,
                "demos":      ls.demos,
                "assists":    ls.assists,
                "score":      ls.score,
                "boost":      ls.boost,
                "speed":      round(ls.speed),
                "efficiency": round(ls.efficiency_score, 3),
                "aggression": round(ls.aggression_score, 3),
                "demolished": ls.demolished,
            }

        return {
            "match":        self.match.to_dict(),
            "players":      players_out,
            "self":         self_data,
            "self_profile": self.sdb.profile.to_dict(),
            "session":      [r.to_dict() for r in self.sdb.session_records()],
            "db_size":      self.pdb.count(),
            "report_ready": self.report_ready,
            "last_report":  self.last_report.to_dict() if self.last_report else None,
        }

    def _push(self):
        """Replace queue with latest — overlay always gets freshest state."""
        snap = self.snapshot()
        while not self.state_queue.empty():
            try:
                self.state_queue.get_nowait()
            except queue.Empty:
                break
        try:
            self.state_queue.put_nowait(snap)
        except queue.Full:
            pass

    def _by_name(self, name: str) -> Optional[LivePlayerState]:
        for ls in self.live.values():
            if ls.name == name:
                return ls
        return None
