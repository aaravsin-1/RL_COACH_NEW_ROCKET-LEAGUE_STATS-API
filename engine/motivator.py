"""
motivator.py
Generates a single contextual motivational message after each match.
Specific, not generic. Based on streak, tilt, performance, and trend.
"""
from __future__ import annotations
from models.self_profile import SelfProfile
from models.session_record import MatchRecord


def generate(profile: SelfProfile, record: MatchRecord,
             tilt: bool, session_records: list[MatchRecord]) -> str:

    streak  = profile.current_streak
    eff     = record.efficiency
    avg_eff = profile.avg_efficiency
    acc     = record.shot_accuracy
    won     = record.won

    # Tilt warning — highest priority
    if tilt:
        return (
            f"Your efficiency has dropped across the last few games. "
            f"This is a tilt pattern — not a skill issue. "
            f"Take 10 minutes before queuing again."
        )

    # Session performance
    session_effs = [r.efficiency for r in session_records]
    trending_up   = len(session_effs) >= 3 and session_effs[-1] > session_effs[-3]
    trending_down = len(session_effs) >= 3 and session_effs[-1] < session_effs[-3] - 0.10

    # Win streaks
    if streak >= 5:
        return f"5 wins in a row. You're locked in — don't start gambling now. Keep the reads clean."
    if streak >= 3:
        return f"{streak} win streak. Efficiency is {eff:.0%} — above your avg. Ride this."

    # Loss streaks
    if streak <= -4:
        return (
            f"{abs(streak)} in a row. Stop. Your avg efficiency is {avg_eff:.0%} "
            f"and you're at {eff:.0%} this match. Come back fresh."
        )
    if streak <= -2:
        return (
            f"Down {abs(streak)}. Your shot accuracy this match was {acc:.0%}. "
            f"{'Shooting too much — wait for better looks.' if acc < 0.25 else 'The shots are going in — rotations are the issue.'}"
        )

    # Just won
    if won:
        if eff > avg_eff + 0.10:
            return f"Clean win. Efficiency was {eff:.0%} — {(eff-avg_eff):.0%} above your average. This is your level."
        if trending_up:
            return f"Win and trending up across the session. Keep the same approach next game."
        return f"Good win. Efficiency {eff:.0%}. {'Shot accuracy was excellent.' if acc > 0.5 else 'Work on shot selection next game.'}"

    # Just lost
    if trending_down:
        return (
            f"Performance has dipped across the session. "
            f"Efficiency dropped to {eff:.0%}. Consider wrapping up for today."
        )
    if eff > avg_eff:
        return f"Loss but you played above your average ({eff:.0%} vs {avg_eff:.0%}). That's a good loss — keep queuing."
    if record.saves >= 2:
        return f"You made {record.saves} saves — the defence was there. Goals need more looks."
    return f"Efficiency {eff:.0%}, avg is {avg_eff:.0%}. One thing to fix: {'shot selection' if acc < 0.3 else 'touch quality in transition'}."
