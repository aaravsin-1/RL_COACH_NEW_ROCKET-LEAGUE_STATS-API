"""
training_engine.py
Maps weak performance metrics to specific Rocket League drills.
Tuned for 2v2.
"""
from __future__ import annotations
from models.session_record import MatchRecord
from models.self_profile import SelfProfile


DRILLS = {
    "shot_accuracy": {
        "title":  "Shot Accuracy",
        "why":    "Your shots per goal ratio is high — shooting but not converting.",
        "drills": [
            "Striker training packs (Pro / All-Star difficulty)",
            "Lethamyr ring maps — forces accurate aiming",
            "Free play: shoot from awkward angles only",
        ],
        "time": "15 min",
    },
    "efficiency": {
        "title":  "Touch Quality",
        "why":    "Touches aren't producing enough value — too many neutral touches.",
        "drills": [
            "Dribbling + carry → shot combo drills",
            "Wall play workshop maps",
            "No-bounce challenge: control every touch",
        ],
        "time": "20 min",
    },
    "boost": {
        "title":  "Boost Management",
        "why":    "Burning boost without sufficient speed output.",
        "drills": [
            "Low-boost free play (cap yourself at 33 boost)",
            "Boost pad routing — learn every pad on standard maps",
            "No-boost scrimmage",
        ],
        "time": "15 min",
    },
    "rotation": {
        "title":  "2v2 Rotations",
        "why":    "High risk score suggests overcommitting or double-committing in 2s.",
        "drills": [
            "Shadowing drill with a partner",
            "Watch your own replays: mark every double-commit",
            "Passive 3rd-man practice — force yourself to rotate back",
        ],
        "time": "20 min",
    },
    "saves": {
        "title":  "Defensive Positioning",
        "why":    "Low save rate — getting caught out of position.",
        "drills": [
            "Goalie training packs (Bronze → Gold)",
            "Recovery drills: get back faster after forward plays",
            "Workshop: goal line save scenarios",
        ],
        "time": "15 min",
    },
    "demos": {
        "title":  "Game Sense over Demos",
        "why":    "Chasing demos in 2s leaves your partner exposed.",
        "drills": [
            "Play a full session without intentionally demoing",
            "Focus: positioning reward > demo reward",
            "Watch a GC 2v2 VOD — count how rarely they demo-chase",
        ],
        "time": "10 min",
    },
}


def prescribe(record: MatchRecord, profile: SelfProfile) -> list[dict]:
    """Return up to 3 prioritised drill recommendations."""
    scores = []

    # Shot accuracy
    if record.shots >= 2 and record.shot_accuracy < 0.30:
        scores.append(("shot_accuracy", 1 - record.shot_accuracy))

    # Efficiency vs average
    if record.efficiency < profile.avg_efficiency - 0.05:
        scores.append(("efficiency", profile.avg_efficiency - record.efficiency))

    # Boost
    if record.boost_eff < 0.35:
        scores.append(("boost", 0.35 - record.boost_eff))

    # Risk / rotation
    if record.risk > 0.60:
        scores.append(("rotation", record.risk - 0.60))

    # Saves
    if record.saves == 0 and record.touches > 5:
        scores.append(("saves", 0.3))

    # Demo chasing in 2s
    if record.demos >= 3:
        scores.append(("demos", record.demos * 0.1))

    # Sort by priority score, return top 3
    scores.sort(key=lambda x: x[1], reverse=True)
    result = []
    for key, _ in scores[:3]:
        d = DRILLS[key].copy()
        d["key"] = key
        result.append(d)

    # Always give at least one drill
    if not result:
        result.append({**DRILLS["efficiency"], "key": "efficiency"})

    return result
