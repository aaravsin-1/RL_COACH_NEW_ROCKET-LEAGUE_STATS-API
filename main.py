"""
main.py — RL Coach entry point.

Thread layout:
  Main thread   → PyQt5 overlay (Qt requires main thread)
  Thread 2      → Raw TCP client (connects to RL, feeds session)
"""
import logging
import sys
import threading

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("rl_coach.log", mode="a", encoding="utf-8"),
    ],
)
log = logging.getLogger("rl_coach")
for _lib in ("PyQt5","werkzeug","engineio","socketio"):
    logging.getLogger(_lib).setLevel(logging.WARNING)

# ── Imports ────────────────────────────────────────────────────────────────────
from storage.player_db import PlayerDB
from storage.self_db   import SelfDB
from session            import GameSession
from ws_client          import run_client
from overlay            import run_overlay


def main():
    log.info("=" * 55)
    log.info("  RL COACH — Opponent Intelligence + Self Analysis")
    log.info(f"  Player: dogmiv  |  Mode: 2v2")
    log.info("=" * 55)

    player_db = PlayerDB()
    self_db   = SelfDB()
    session   = GameSession(player_db, self_db)

    # TCP client on background thread
    tcp_thread = threading.Thread(
        target  = run_client,
        args    = (session,),
        daemon  = True,
        name    = "tcp-client",
    )
    tcp_thread.start()

    # Overlay on main thread (Qt requirement)
    log.info("Starting overlay...")
    run_overlay(session.state_queue)

    log.info("Overlay closed. Exiting.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Shutting down.")
