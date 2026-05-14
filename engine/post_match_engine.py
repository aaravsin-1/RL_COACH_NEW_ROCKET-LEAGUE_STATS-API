"""
post_match_engine.py
Builds the complete post-match report.
Uses match_duration passed from session (match-level timer, never reset).
"""
from __future__ import annotations
import time as _time
from models.live_state import LivePlayerState
from models.session_record import MatchRecord
from models.self_profile import SelfProfile
from engine.decision_audit import DecisionAuditor
from engine import motivator, training_engine


def build_report(
    live:            LivePlayerState,
    auditor:         DecisionAuditor,
    profile:         SelfProfile,
    won:             bool,
    team_score:      int,
    opp_score:       int,
    arena:           str,
    session_records: list,
    match_duration:  int = 300,   # seconds, from MatchState.created_at
) -> MatchRecord:

    moments      = auditor.finalise()
    accuracy     = live.shot_accuracy

    # ── Strengths ─────────────────────────────────────────────────
    strengths = []
    if accuracy > 0.50 and live.shots >= 2:
        strengths.append(f"Shot accuracy {accuracy:.0%} — converting looks well.")
    if live.saves >= 2:
        strengths.append(f"{live.saves} saves — solid defensive positioning.")
    if live.assists >= 1:
        strengths.append(f"{live.assists} assist(s) — reading teammate plays.")
    if live.efficiency_score > profile.avg_efficiency + 0.08:
        strengths.append("Efficiency above your average — cleaner touches than usual.")
    if live.boost_efficiency > 0.60 and live.total_boost_consumed > 20:
        strengths.append("Excellent boost efficiency — getting speed from every pad.")
    if sum(1 for m in moments if m["severity"] == "good") >= 2:
        strengths.append("Multiple positive touch sequences — good decision-making.")
    if not strengths:
        strengths.append("Stayed competitive — use the drills below to sharpen up.")

    # ── Weaknesses ────────────────────────────────────────────────
    weaknesses = []
    if accuracy < 0.25 and live.shots >= 3:
        weaknesses.append(f"Shot accuracy only {accuracy:.0%} — wait for better looks.")
    if live.efficiency_score < profile.avg_efficiency - 0.08:
        weaknesses.append(
            f"Efficiency {live.efficiency_score:.0%} below your avg "
            f"{profile.avg_efficiency:.0%} — low value touches."
        )
    if live.boost_efficiency < 0.30 and live.total_boost_consumed > 20:
        weaknesses.append("Boost wasted — burning without enough speed output.")
    if live.demos >= 3:
        weaknesses.append(f"{live.demos} demos — chasing demos in 2s leaves partner exposed.")
    bad = sum(1 for m in moments if m["severity"] == "bad")
    if bad >= 2:
        weaknesses.append(f"{bad} touches led to conceded goals — watch overcommitting.")
    if live.shots > 5 and live.goals == 0:
        weaknesses.append("5+ shots, 0 goals — shot selection needs work.")
    if not weaknesses:
        weaknesses.append("No major issues detected. Maintain this standard.")

    # ── Mock record for training prescription ─────────────────────
    mock         = MatchRecord(guid="tmp", won=won)
    mock.goals   = live.goals;   mock.shots   = live.shots
    mock.saves   = live.saves;   mock.demos   = live.demos
    mock.touches = live.touches; mock.efficiency    = live.efficiency_score
    mock.risk    = live.risk_score; mock.boost_eff  = live.boost_efficiency
    mock.shot_accuracy = accuracy

    tilt = (
        len(session_records) >= 3 and
        session_records[0].efficiency - live.efficiency_score > 0.15
    )

    record = MatchRecord(
        guid          = f"match_{int(_time.time())}",
        won           = won,
        team_score    = team_score,
        opp_score     = opp_score,
        goals         = live.goals,
        shots         = live.shots,
        assists       = live.assists,
        saves         = live.saves,
        demos         = live.demos,
        touches       = live.touches,
        score         = live.score,
        aggression    = live.aggression_score,
        efficiency    = live.efficiency_score,
        risk          = live.risk_score,
        boost_eff     = live.boost_efficiency,
        shot_accuracy = accuracy,
        duration_secs = match_duration,   # ← real match duration
        arena         = arena,
        moments       = moments,
        strengths     = strengths,
        weaknesses    = weaknesses,
        drills        = training_engine.prescribe(mock, profile),
    )
    record.motivator = motivator.generate(profile, record, tilt, session_records)
    return record
