"""
ws_client.py — Raw TCP client for RL Stats API.
NO WebSocket, NO HTTP GET. Just bare TCP + JSON stream.
Config: [TAGame.MatchStatsExporter_TA] in DefaultStatsAPI.ini
"""
from __future__ import annotations
import json, logging, socket, time
from session import GameSession

log = logging.getLogger(__name__)
RECONNECT_DELAY = 3
SOCKET_TIMEOUT  = 15
MAX_BUF         = 1_000_000


def extract_json_objects(buf: bytes) -> tuple[list[bytes], bytes]:
    objects, i = [], 0
    while i < len(buf):
        if buf[i:i+1] == b"{":
            depth, in_str, escape, j = 0, False, False, i
            while j < len(buf):
                c = buf[j:j+1]
                if escape:       escape = False
                elif c == b"\\": escape = True
                elif c == b'"':  in_str = not in_str
                elif not in_str:
                    if   c == b"{": depth += 1
                    elif c == b"}":
                        depth -= 1
                        if depth == 0:
                            objects.append(buf[i:j+1])
                            i = j + 1
                            break
                j += 1
            else: break
        else: i += 1
    return objects, buf[i:]


def _stream(session: GameSession):
    from config import RL_WS_HOST, RL_WS_PORT
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(SOCKET_TIMEOUT)
    try:
        sock.connect((RL_WS_HOST, RL_WS_PORT))
        log.info("Connected to Rocket League Stats API \u2713")
        buf = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk: raise ConnectionError("RL closed socket.")
            buf += chunk
            objects, buf = extract_json_objects(buf)
            for raw in objects:
                try:
                    msg   = json.loads(raw.decode("utf-8"))
                    event = msg.get("Event", "")
                    data  = msg.get("Data", {})
                    if isinstance(data, str):
                        try: data = json.loads(data)
                        except: pass
                    session.on_event(event, data)
                except Exception as e:
                    log.debug(f"Dispatch error: {e}")
            if len(buf) > MAX_BUF: buf = b""
    finally:
        try: sock.close()
        except: pass


def run_client(session: GameSession):
    from config import RL_WS_HOST, RL_WS_PORT
    addr = f"{RL_WS_HOST}:{RL_WS_PORT}"
    while True:
        try:
            log.info(f"Connecting to {addr} ...")
            _stream(session)
        except (OSError, ConnectionRefusedError) as e:
            log.warning(f"Not connected ({e}). Retry in {RECONNECT_DELAY}s ...")
        except ConnectionError as e:
            log.info(f"Disconnected: {e}. Retry in {RECONNECT_DELAY}s ...")
        except socket.timeout:
            log.warning(f"Timeout. Retry in {RECONNECT_DELAY}s ...")
        except Exception as e:
            log.error(f"TCP error: {e}", exc_info=True)
        time.sleep(RECONNECT_DELAY)
