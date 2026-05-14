from __future__ import annotations
from engine.analysis_engine import PlayerInsight

CRIT = "critical"
WARN = "warn"
INFO = "info"


class CoachingEngine:
    def tips(self, ins: PlayerInsight) -> list[dict]:
        out = []
        la, le = ins.live_aggression, ins.live_efficiency
        style   = ins.playstyle
        conf    = ins.confidence
        acc     = ins.goals / max(ins.shots, 1)

        # Playstyle counters
        if style == "Ball-Chaser":
            out.append((CRIT, "Ball-chaser — fake challenge, they WILL commit first every time."))
            out.append((WARN, "Don't 50/50. Let them overextend and take the free ball."))
        elif style == "Aggressive-Efficient":
            out.append((WARN, "Efficient aggressor — only challenge with clear advantage."))
            out.append((INFO, "Match their tempo or they'll outpace your rotation."))
        elif style == "Calculated-Passive":
            out.append((WARN, "Passive defender — push constant pressure, force their hand."))
            out.append((INFO, "They sit deep and wait. Don't let them reset."))
        elif style == "Passive":
            out.append((INFO, "Low impact — focus your own rotations, they're not a threat."))

        # Live aggression extremes
        if la > 0.75:
            out.append((CRIT, "⚡ Extremely aggressive right now — hang back, let them overextend."))
        elif la < 0.20:
            out.append((WARN, "Very passive this match — push them, they're not contesting."))

        # Deviation
        if ins.more_aggressive and conf != "none":
            out.append((WARN, f"Playing MORE aggressive than usual ({ins.hist_aggression:.0%} → {la:.0%})."))
        if ins.more_passive and conf != "none":
            out.append((INFO, f"Playing more passive than usual — possibly low boost or tilted."))

        # Demos
        if ins.demos >= 2:
            out.append((WARN, "Demo-hungry — dodge sideways after clears, don't drive straight."))

        # Boost
        if ins.live_boost_eff < 0.25:
            out.append((INFO, "Wasting boost — time challenges when they're likely empty."))
        elif ins.live_boost_eff > 0.70:
            out.append((WARN, "Excellent boost management — expect bursts of speed."))

        # Shooting
        if ins.shots >= 3 and acc > 0.60:
            out.append((CRIT, f"High accuracy ({acc:.0%}) — do NOT leave net exposed."))
        elif ins.shots >= 3 and acc < 0.20:
            out.append((INFO, f"Low accuracy ({acc:.0%}) — challenge their shots freely."))

        # Saves
        if ins.saves >= 2:
            out.append((INFO, "Active keeper — test with low hard shots."))

        # Confidence context
        if conf == "none":
            out.append((INFO, f"First time seeing {ins.name}. Tips get better each match."))
        elif conf == "low":
            out.append((INFO, f"Limited data ({ins.matches_seen} match). Treat as preliminary."))

        order = {CRIT: 0, WARN: 1, INFO: 2}
        out.sort(key=lambda x: order[x[0]])
        return [{"level": lvl, "text": txt} for lvl, txt in out[:5]]
