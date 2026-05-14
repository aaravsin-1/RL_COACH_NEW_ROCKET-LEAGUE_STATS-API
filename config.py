# ================================================================
#  RL COACH — Configuration
# ================================================================

# ── Your identity ────────────────────────────────────────────────
LOCAL_PLAYER_NAME = "dogmiv"
GAME_MODE         = "2v2"

# ── Rocket League Stats API ──────────────────────────────────────
RL_WS_HOST = "127.0.0.1"
RL_WS_PORT = 49123

# ── Overlay ──────────────────────────────────────────────────────
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5000

# UI scale factor — increase if text is too small (e.g. 1.2 or 1.4)
UI_SCALE = 1.4

# ── Storage ──────────────────────────────────────────────────────
PLAYER_DB_PATH     = "data/players.json"
SELF_DB_PATH       = "data/self_profile.json"
MATCH_HISTORY_PATH = "data/match_history.json"

# ── Profile learning ─────────────────────────────────────────────
# EMA alpha: used for BEHAVIOURAL metrics (aggression/efficiency/risk)
# Counting stats (goals/saves/etc) use true running average instead
EMA_ALPHA         = 0.25
MAX_MATCH_HISTORY = 100

# ── Session ──────────────────────────────────────────────────────
SESSION_WINDOW_HOURS = 4

# ── Confidence thresholds ─────────────────────────────────────────
CONFIDENCE_LOW  = 1
CONFIDENCE_MED  = 5
CONFIDENCE_HIGH = 12

# ── Playstyle classification ──────────────────────────────────────
AGG_HIGH = 0.65
AGG_LOW  = 0.30
EFF_HIGH = 0.55
EFF_LOW  = 0.25

# ── Tilt detection ───────────────────────────────────────────────
TILT_EFF_DROP = 0.15
TILT_WINDOW   = 3

# ── Decision audit ───────────────────────────────────────────────
AUDIT_WINDOW_SECS = 12.0
