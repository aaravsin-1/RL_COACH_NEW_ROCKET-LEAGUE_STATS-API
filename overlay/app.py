"""
overlay/app.py

Fix 1: adjustSize() only called when card count changes, not every poll.
Fix 5: All text goes through L() which applies UI_SCALE from config.
Fix 6: Poll timer 400ms (was 100ms). Clock interpolation still at 1s.
Fix 2: (session.py handles replay flag; overlay is unaffected.)
"""
from __future__ import annotations
import sys
import time
import queue as _queue

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QMenu, QAction,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QPainter

from config import UI_SCALE

# ── Palette ───────────────────────────────────────────────────────────────────
PANEL  = "rgba(12,20,30,205)"
BORDER = "#1a2535"
ACCENT = "#00e5ff"
RED    = "#ff4060"
ORANGE = "#ffaa20"
GREEN  = "#a0ff40"
GOLD   = "#ffd060"
TEXT   = "#c8dae8"
TDIM   = "#4a6880"
BLUE_T = "#0060ff"
ORG_T  = "#ff6000"

APP_STYLE = f"""
QWidget     {{ background:transparent; color:{TEXT};
               font-family:'Segoe UI',Arial,sans-serif; }}
QLabel      {{ background:transparent; }}
QPushButton {{ background:transparent; color:{TDIM}; border:none; padding:1px 5px; }}
QPushButton:hover {{ color:{ACCENT}; }}
"""


# ── Fix 5: Central text scaling ───────────────────────────────────────────────
# All text in the overlay goes through L(). Changing UI_SCALE in config.py
# scales every label uniformly without touching individual widget code.
def L(text="", color=TEXT, bold=False, size=12, align=Qt.AlignLeft) -> QLabel:
    scaled = max(8, int(size * UI_SCALE))
    lb = QLabel(text)
    lb.setStyleSheet(
        f"color:{color};font-size:{scaled}px;"
        f"font-weight:{'700' if bold else '400'};"
    )
    lb.setAlignment(align)
    return lb


def hsep() -> QFrame:
    f = QFrame(); f.setFrameShape(QFrame.HLine)
    f.setStyleSheet(f"background:#1a2535;max-height:1px;min-height:1px;")
    return f


class MeterBar(QWidget):
    def __init__(self, value=0.0, color=ACCENT, h=4):
        super().__init__()
        self._v = value; self._c = color
        self.setFixedHeight(max(3, int(h * UI_SCALE)))
        self.setMinimumWidth(40)

    def set_value(self, v: float):
        self._v = max(0.0, min(1.0, v)); self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(0, 0, self.width(), self.height(), QColor(255, 255, 255, 18))
        fw = int(self._v * self.width())
        if fw > 0:
            p.fillRect(0, 0, fw, self.height(), QColor(self._c))


# ── Opponent Card ─────────────────────────────────────────────────────────────
class OpponentCard(QFrame):
    def __init__(self):
        super().__init__()
        self._tip_labels: list[QLabel] = []
        self._build()

    def _build(self):
        self.setStyleSheet(
            f"QFrame{{background:{PANEL};border:1px solid {BORDER};"
            f"border-left:3px solid {BORDER};border-radius:3px;}}"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6); root.setSpacing(3)

        hdr = QHBoxLayout(); hdr.setSpacing(5)
        self._name  = L("", TEXT, bold=True, size=13)
        self._style = L("", TDIM, size=9)
        self._rank  = L("", GOLD, size=9)
        self._conf  = L("●", "#3a5070", size=10)
        hdr.addWidget(self._name); hdr.addWidget(self._style)
        hdr.addStretch()
        hdr.addWidget(self._rank); hdr.addWidget(self._conf)
        root.addLayout(hdr)

        sr = QHBoxLayout(); sr.setSpacing(8)
        self._sv: dict[str, QLabel] = {}
        for key, lbl in [("G","G"),("SH","SH"),("SV","SV"),
                          ("TCH","TCH"),("DM","DM"),("ACC","ACC")]:
            col = QVBoxLayout(); col.setSpacing(0)
            v = L("–", TEXT, bold=True, size=14, align=Qt.AlignHCenter)
            t = L(lbl,  TDIM, size=8,  align=Qt.AlignHCenter)
            col.addWidget(v); col.addWidget(t)
            self._sv[key] = v; sr.addLayout(col)
        root.addLayout(sr)

        self._bars: dict[str, MeterBar] = {}
        self._pcts: dict[str, QLabel]   = {}
        for lbl, color in [("AGG", RED), ("EFF", GREEN), ("RSK", ORANGE)]:
            row = QHBoxLayout(); row.setSpacing(5)
            row.addWidget(L(lbl, TDIM, size=8), 0)
            bar = MeterBar(0.0, color); self._bars[lbl] = bar
            row.addWidget(bar, 1)
            pct = L("0%", TDIM, size=8); self._pcts[lbl] = pct
            row.addWidget(pct, 0)
            root.addLayout(row)

        self._dev      = L("", ORANGE, size=9); root.addWidget(self._dev)
        self._tips_lay = QVBoxLayout(); self._tips_lay.setSpacing(2)
        root.addLayout(self._tips_lay)

    def update(self, data: dict):
        stats = data.get("stats", {})
        live  = data.get("live",  {})
        hist  = data.get("history", {})
        dev   = data.get("deviation", {})
        tips  = data.get("tips", [])

        c = BLUE_T if data.get("team_num", 1) == 0 else ORG_T
        self.setStyleSheet(
            f"QFrame{{background:{PANEL};border:1px solid {BORDER};"
            f"border-left:3px solid {c};border-radius:3px;}}"
        )
        self._name.setText(data.get("name","?"))
        self._style.setText(hist.get("playstyle","").upper())
        rk = hist.get("rank","")
        self._rank.setText("" if rk in ("","Unknown") else rk)

        conf_c = {"none":"#3a5070","low":ORANGE,"medium":ORANGE,"high":GREEN}
        self._conf.setStyleSheet(
            f"color:{conf_c.get(hist.get('confidence','none'),'#3a5070')};font-size:{int(10*UI_SCALE)}px;"
        )
        self._conf.setToolTip(
            f"Confidence: {hist.get('confidence','none')} ({hist.get('matches',0)} matches)"
        )

        sh = stats.get("shots",0); gl = stats.get("goals",0)
        acc = gl/sh if sh>0 else 0.0
        self._sv["G"].setText(str(gl))
        self._sv["SH"].setText(str(sh))
        self._sv["SV"].setText(str(stats.get("saves",0)))
        self._sv["TCH"].setText(str(stats.get("touches",0)))
        self._sv["DM"].setText(str(stats.get("demos",0)))
        self._sv["ACC"].setText(f"{acc:.0%}")
        self._sv["ACC"].setStyleSheet(
            f"color:{'#a0ff40' if acc>0.5 else '#ffaa20' if acc>0.25 else '#ff4060'};"
            f"font-size:{int(14*UI_SCALE)}px;font-weight:700;"
        )

        for key, src in [("AGG","aggression"),("EFF","efficiency"),("RSK","risk")]:
            v = live.get(src, 0.0)
            self._bars[key].set_value(v); self._pcts[key].setText(f"{v:.0%}")

        self._dev.setText(
            "▲ MORE AGGRESSIVE THAN USUAL" if dev.get("aggressive")
            else "▼ MORE PASSIVE THAN USUAL" if dev.get("passive") else ""
        )

        for lb in self._tip_labels: lb.setParent(None)
        self._tip_labels.clear()
        tip_c = {"critical": RED, "warn": ORANGE, "info": ACCENT}
        for tip in tips[:3]:
            lvl = ("critical"
                   if any(w in tip for w in ("FAKE","⚡","VERY","commits","always commit"))
                   else "warn"
                   if any(w in tip for w in ("Demo","pressure","aggress","passive","boost"))
                   else "info")
            icon = {"critical":"⚡","warn":"⚠","info":"·"}[lvl]
            lb = L(f"{icon} {tip}", tip_c[lvl], size=10)
            lb.setWordWrap(True)
            self._tips_lay.addWidget(lb)
            self._tip_labels.append(lb)


# ── Self Panel ────────────────────────────────────────────────────────────────
class SelfPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(
            f"QFrame{{background:{PANEL};border:1px solid {BORDER};"
            f"border-left:3px solid {ACCENT};border-radius:3px;}}"
        )
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6); root.setSpacing(3)

        hdr = QHBoxLayout(); hdr.setSpacing(5)
        self._name   = L("YOU",  ACCENT, bold=True, size=12)
        self._streak = L("–",    TEXT,   bold=True, size=14)
        self._rec    = L("",     TDIM,   size=10)
        hdr.addWidget(self._name); hdr.addStretch()
        hdr.addWidget(self._rec); hdr.addWidget(self._streak)
        root.addLayout(hdr)

        sr = QHBoxLayout(); sr.setSpacing(8)
        self._sv: dict[str, QLabel] = {}
        for key, lbl in [("G","G"),("SH","SH"),("SV","SV"),
                          ("TCH","TCH"),("BST","BST")]:
            col = QVBoxLayout(); col.setSpacing(0)
            v = L("–",  TEXT, bold=True, size=14, align=Qt.AlignHCenter)
            t = L(lbl,  TDIM, size=8,   align=Qt.AlignHCenter)
            col.addWidget(v); col.addWidget(t)
            self._sv[key] = v; sr.addLayout(col)
        root.addLayout(sr)

        er = QHBoxLayout(); er.setSpacing(5)
        er.addWidget(L("EFF", TDIM, size=8))
        self._eff_bar = MeterBar(0.0, GREEN)
        er.addWidget(self._eff_bar, 1)
        self._eff_pct = L("0%", TDIM, size=8)
        er.addWidget(self._eff_pct)
        root.addLayout(er)

        self._mot = L("", TDIM, size=10)
        self._mot.setWordWrap(True)
        self._mot.setStyleSheet(
            f"color:{TDIM};font-size:{int(10*UI_SCALE)}px;font-style:italic;"
        )
        root.addWidget(self._mot)

    def update(self, self_data: dict, profile: dict, last_report: dict):
        if not self_data: return
        self._name.setText(f"YOU: {self_data.get('name','dogmiv')}")

        sk  = profile.get("streak_type","none")
        sc  = GREEN if sk=="win" else RED if sk=="loss" else TEXT
        self._streak.setText(profile.get("streak_label","–"))
        self._streak.setStyleSheet(
            f"color:{sc};font-size:{int(14*UI_SCALE)}px;font-weight:700;"
        )

        sw = profile.get("session_wins",    0)
        sm = profile.get("session_matches", 0)
        self._rec.setText(f"{sw}W-{sm-sw}L TODAY")

        self._sv["G"].setText(str(self_data.get("goals",  0)))
        self._sv["SH"].setText(str(self_data.get("shots", 0)))
        self._sv["SV"].setText(str(self_data.get("saves", 0)))
        self._sv["TCH"].setText(str(self_data.get("touches",0)))

        boost = self_data.get("boost", 0)
        self._sv["BST"].setText(f"{boost}%")
        bc = GREEN if boost>60 else ORANGE if boost>25 else RED
        self._sv["BST"].setStyleSheet(
            f"color:{bc};font-size:{int(14*UI_SCALE)}px;font-weight:700;"
        )

        eff = self_data.get("efficiency", 0.0)
        self._eff_bar.set_value(eff); self._eff_pct.setText(f"{eff:.0%}")

        if last_report and last_report.get("motivator"):
            self._mot.setText(f'"{last_report["motivator"]}"')


# ── Match Bar ─────────────────────────────────────────────────────────────────
class MatchBar(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(
            f"QFrame{{background:{PANEL};border:1px solid {BORDER};border-radius:3px;}}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10,4,10,4); lay.setSpacing(6)

        self._bn = L("BLUE",   BLUE_T, bold=True, size=11)
        self._bs = L("–",      BLUE_T, bold=True, size=22)
        self._os = L("–",      ORG_T,  bold=True, size=22, align=Qt.AlignRight)
        self._on = L("ORANGE", ORG_T,  bold=True, size=11, align=Qt.AlignRight)
        self._tm = L("5:00",   ACCENT, bold=True, size=18, align=Qt.AlignHCenter)
        self._ot = L("",       GOLD,   bold=True, size=9,  align=Qt.AlignHCenter)

        lay.addWidget(self._bn); lay.addWidget(self._bs); lay.addStretch()
        mid = QVBoxLayout(); mid.setSpacing(0)
        mid.addWidget(self._tm); mid.addWidget(self._ot)
        lay.addLayout(mid)
        lay.addStretch()
        lay.addWidget(self._os); lay.addWidget(self._on)

    def set_time(self, seconds: int, overtime: bool, has_winner: bool, winner: str):
        self._tm.setText(f"{seconds//60}:{seconds%60:02d}")
        if has_winner:
            self._ot.setText(f"🏆 {winner.upper()} WIN")
            self._ot.setStyleSheet(f"color:{GREEN};font-size:{int(9*UI_SCALE)}px;font-weight:700;")
        elif overtime:
            self._ot.setText("OVERTIME")
            self._ot.setStyleSheet(f"color:{GOLD};font-size:{int(9*UI_SCALE)}px;font-weight:700;")
        else:
            self._ot.setText("")

    def update(self, match: dict):
        self.set_time(
            match.get("time_seconds", 300),
            match.get("overtime", False),
            match.get("has_winner", False),
            match.get("winner", ""),
        )
        for team in match.get("teams", []):
            c     = "#" + team.get("color","0060FF")
            name  = team.get("name","TEAM").upper()[:12]
            score = str(team.get("score",0))
            if team.get("team_num",0) == 0:
                self._bn.setText(name)
                self._bn.setStyleSheet(f"color:{c};font-size:{int(11*UI_SCALE)}px;font-weight:700;")
                self._bs.setText(score)
                self._bs.setStyleSheet(f"color:{c};font-size:{int(22*UI_SCALE)}px;font-weight:700;")
            else:
                self._on.setText(name)
                self._on.setStyleSheet(f"color:{c};font-size:{int(11*UI_SCALE)}px;font-weight:700;")
                self._os.setText(score)
                self._os.setStyleSheet(f"color:{c};font-size:{int(22*UI_SCALE)}px;font-weight:700;")


# ── Post-Match Popup ──────────────────────────────────────────────────────────
class PostMatchPopup(QWidget):
    def __init__(self):
        super().__init__(None,
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.96)
        self._drag_pos = None
        self._build()
        self.hide()

    def _build(self):
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0)
        box = QFrame()
        box.setStyleSheet(
            f"QFrame{{background:rgba(8,14,22,240);"
            f"border:1px solid {ACCENT};border-radius:5px;}}"
        )
        lay = QVBoxLayout(box)
        lay.setContentsMargins(12,10,12,12); lay.setSpacing(7)
        outer.addWidget(box)

        tr = QHBoxLayout(); tr.setSpacing(6)
        tr.addWidget(L("POST-MATCH REPORT", ACCENT, bold=True, size=10))
        tr.addStretch()
        self._res = L("", TEXT, bold=True, size=24)
        self._scr = L("", TDIM, size=13)
        btn = QPushButton("×")
        btn.setStyleSheet(f"color:{RED};font-size:{int(16*UI_SCALE)}px;")
        btn.clicked.connect(self.hide)
        tr.addWidget(self._res); tr.addWidget(self._scr); tr.addWidget(btn)
        lay.addLayout(tr); lay.addWidget(hsep())

        self._mot = L("", TEXT, size=11)
        self._mot.setWordWrap(True)
        self._mot.setStyleSheet(
            f"color:{TEXT};font-size:{int(11*UI_SCALE)}px;font-style:italic;"
            f"background:rgba(0,229,255,0.06);padding:7px;border-radius:3px;"
        )
        lay.addWidget(self._mot)

        sw = QHBoxLayout(); sw.setSpacing(8)
        sf = QFrame()
        sf.setStyleSheet(f"QFrame{{background:rgba(160,255,64,0.05);"
                         f"border:1px solid rgba(160,255,64,0.2);border-radius:3px;}}")
        self._sl = QVBoxLayout(sf)
        self._sl.setContentsMargins(8,6,8,6); self._sl.setSpacing(2)
        self._sl.addWidget(L("✓ STRENGTHS", GREEN, bold=True, size=9))
        sw.addWidget(sf)

        wf = QFrame()
        wf.setStyleSheet(f"QFrame{{background:rgba(255,64,96,0.05);"
                         f"border:1px solid rgba(255,64,96,0.2);border-radius:3px;}}")
        self._wl = QVBoxLayout(wf)
        self._wl.setContentsMargins(8,6,8,6); self._wl.setSpacing(2)
        self._wl.addWidget(L("⚠ IMPROVE", RED, bold=True, size=9))
        sw.addWidget(wf)
        lay.addLayout(sw)

        lay.addWidget(L("DECISION AUDIT", ACCENT, bold=True, size=9))
        self._ml = QVBoxLayout(); self._ml.setSpacing(2); lay.addLayout(self._ml)

        lay.addWidget(hsep())
        lay.addWidget(L("TODAY'S TRAINING", ACCENT, bold=True, size=9))
        self._dl = QVBoxLayout(); self._dl.setSpacing(5); lay.addLayout(self._dl)

        self.setFixedWidth(int(430 * UI_SCALE))

    @staticmethod
    def _clr(layout):
        while layout.count():
            it = layout.takeAt(0)
            if it.widget(): it.widget().deleteLater()

    def show_report(self, report: dict):
        won = report.get("won", False)
        self._res.setText("WIN" if won else "LOSS")
        self._res.setStyleSheet(
            f"color:{'#a0ff40' if won else '#ff4060'};"
            f"font-size:{int(24*UI_SCALE)}px;font-weight:700;"
        )
        dur = report.get("duration_secs", 0)
        self._scr.setText(
            f"  {report.get('team_score',0)} – {report.get('opp_score',0)}"
            f"  ·  {dur//60}:{dur%60:02d}"
        )
        self._mot.setText(f'"{report.get("motivator","")}"')

        self._clr(self._sl)
        self._sl.addWidget(L("✓ STRENGTHS", GREEN, bold=True, size=9))
        for s in report.get("strengths",[])[:3]:
            lb = L(f"· {s}", GREEN, size=10); lb.setWordWrap(True); self._sl.addWidget(lb)

        self._clr(self._wl)
        self._wl.addWidget(L("⚠ IMPROVE", RED, bold=True, size=9))
        for w in report.get("weaknesses",[])[:3]:
            lb = L(f"· {w}", RED, size=10); lb.setWordWrap(True); self._wl.addWidget(lb)

        self._clr(self._ml)
        sc = {"bad": RED, "warn": ORANGE, "good": GREEN}
        for m in report.get("moments",[])[:5]:
            lb = L(
                f"{m.get('icon','·')} [{m.get('time','–')}] {m.get('description','')}",
                sc.get(m.get("severity","warn"), TDIM), size=10
            )
            lb.setWordWrap(True); self._ml.addWidget(lb)
        if not report.get("moments"):
            self._ml.addWidget(L("No significant moments detected.", TDIM, size=10))

        self._clr(self._dl)
        for d in report.get("drills",[])[:2]:
            self._dl.addWidget(
                L(f"📚 {d.get('title','')}  ·  {d.get('time','')}", ACCENT, bold=True, size=10)
            )
            wh = L(d.get("why",""), TDIM, size=9); wh.setWordWrap(True); self._dl.addWidget(wh)
            dr = L("  |  ".join(d.get("drills",[])[:2]), TEXT, size=9)
            dr.setWordWrap(True); self._dl.addWidget(dr)

        self.adjustSize(); self.show(); self.raise_()
        QTimer.singleShot(50000, self.hide)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(e.globalPos() - self._drag_pos)


# ── Main Overlay ──────────────────────────────────────────────────────────────
class RLCoachOverlay(QWidget):
    def __init__(self, state_queue: "_queue.Queue"):
        super().__init__()
        self._q             = state_queue
        self._drag_pos      = None
        self._collapsed     = False
        self._opp_cards:    dict[str, OpponentCard] = {}
        self._last_report   = None
        self._last_opp_count = 0   # Fix 1: track card count for resize gating

        # Clock interpolation state
        self._clock_value:     int   = 300
        self._clock_recv_at:   float = time.time()
        self._clock_overtime:  bool  = False
        self._clock_has_winner:bool  = False
        self._clock_winner:    str   = ""
        self._match_active:    bool  = False

        self._init_window()
        self._build_ui()

        # Fix 6: 400ms poll — fast enough, much less CPU than 100ms
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start(400)

        # Clock tick at 1s — local interpolation when packets stop
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)

    def _init_window(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.93)
        self.setStyleSheet(APP_STYLE)
        self.setFixedWidth(int(320 * UI_SCALE))
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - int(335 * UI_SCALE), 20)

    def _build_ui(self):
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0)

        self._box = QFrame()
        self._box.setStyleSheet(
            f"QFrame{{background:rgba(8,14,22,210);"
            f"border:1px solid {BORDER};border-radius:5px;}}"
        )
        lay = QVBoxLayout(self._box)
        lay.setContentsMargins(6,4,6,6); lay.setSpacing(4)
        outer.addWidget(self._box)

        # Title bar
        tb = QHBoxLayout(); tb.setSpacing(3)
        logo = L("RL COACH", ACCENT, bold=True, size=11)
        logo.setStyleSheet(
            f"color:{ACCENT};font-size:{int(11*UI_SCALE)}px;"
            f"font-weight:700;letter-spacing:2px;"
        )
        self._status = L("● WAITING", TDIM, size=9)
        self._dbsize = L("", TDIM, size=9)
        btn_col  = QPushButton("–")
        btn_col.setFixedSize(int(18*UI_SCALE), int(18*UI_SCALE))
        btn_col.clicked.connect(self._toggle_collapse)
        btn_quit = QPushButton("×")
        btn_quit.setFixedSize(int(18*UI_SCALE), int(18*UI_SCALE))
        btn_quit.setStyleSheet(f"color:{RED};font-size:{int(14*UI_SCALE)}px;")
        btn_quit.clicked.connect(QApplication.quit)
        tb.addWidget(logo); tb.addWidget(self._status)
        tb.addStretch()
        tb.addWidget(self._dbsize); tb.addWidget(btn_col); tb.addWidget(btn_quit)
        lay.addLayout(tb)

        self._mb = MatchBar(); lay.addWidget(self._mb)

        self._body = QWidget()
        bl = QVBoxLayout(self._body)
        bl.setContentsMargins(0,0,0,0); bl.setSpacing(4)
        bl.addWidget(L("OPPONENTS", TDIM, size=9))
        self._opp_lay = QVBoxLayout(); self._opp_lay.setSpacing(4)
        bl.addLayout(self._opp_lay)
        bl.addWidget(hsep())
        self._sp = SelfPanel(); bl.addWidget(self._sp)
        lay.addWidget(self._body)

        self._popup = PostMatchPopup()

    def _toggle_collapse(self):
        self._collapsed = not self._collapsed
        self._body.setVisible(not self._collapsed)
        self.adjustSize()   # resize on collapse toggle is intentional

    def _poll(self):
        """Fix 6: 400ms. Drain entire queue, apply latest."""
        snap = None
        try:
            while True:
                snap = self._q.get_nowait()
        except _queue.Empty:
            pass
        if snap is not None:
            self._apply(snap)

    def _tick_clock(self):
        """Local clock interpolation — keeps ticking during packet droughts."""
        if not self._match_active or self._clock_has_winner:
            return
        elapsed   = int(time.time() - self._clock_recv_at)
        estimated = max(0, self._clock_value - elapsed)
        self._mb.set_time(estimated, self._clock_overtime,
                          self._clock_has_winner, self._clock_winner)

    def _apply(self, snap: dict):
        match   = snap.get("match", {})
        players = snap.get("players", [])
        self_d  = snap.get("self")
        profile = snap.get("self_profile", {})
        report  = snap.get("last_report")

        # Update clock interpolation state
        ts = match.get("time_seconds", self._clock_value)
        if ts != self._clock_value:
            self._clock_value   = ts
            self._clock_recv_at = time.time()
        self._clock_overtime    = match.get("overtime",    False)
        self._clock_has_winner  = match.get("has_winner",  False)
        self._clock_winner      = match.get("winner",      "")
        self._match_active      = match.get("active",      False)

        if self._match_active:
            self._status.setText("● LIVE")
            self._status.setStyleSheet(f"color:{GREEN};font-size:{int(9*UI_SCALE)}px;")
        else:
            self._status.setText("● WAITING")
            self._status.setStyleSheet(f"color:{TDIM};font-size:{int(9*UI_SCALE)}px;")
        self._dbsize.setText(f"DB:{snap.get('db_size',0)}")

        self._mb.update(match)

        # Opponent cards
        opps = [p for p in players if not p.get("is_self")]
        seen = set()
        cards_changed = False

        for p in opps:
            pid = p.get("primary_id", p.get("name",""))
            seen.add(pid)
            if pid not in self._opp_cards:
                card = OpponentCard()
                self._opp_cards[pid] = card
                self._opp_lay.addWidget(card)
                cards_changed = True
            self._opp_cards[pid].update(p)

        for pid in list(self._opp_cards):
            if pid not in seen:
                self._opp_cards[pid].setParent(None)
                del self._opp_cards[pid]
                cards_changed = True

        self._sp.update(self_d, profile, report)

        # Fix 1: only adjustSize when card count changes, not every poll
        if cards_changed:
            self.adjustSize()

        # Post-match popup
        if snap.get("report_ready") and report:
            rid = report.get("guid","")
            if rid != self._last_report:
                self._last_report = rid
                scr = QApplication.primaryScreen().geometry()
                self._popup.move(
                    max(0, scr.width()//2 - int(215*UI_SCALE)),
                    max(0, scr.height()//2 - 250),
                )
                self._popup.show_report(report)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()
        elif e.button() == Qt.MiddleButton:
            self._toggle_collapse()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(e.globalPos() - self._drag_pos)

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{PANEL};border:1px solid {BORDER};"
            f"color:{TEXT};padding:4px;font-size:{int(11*UI_SCALE)}px;}}"
            f"QMenu::item:selected{{background:rgba(0,229,255,0.1);}}"
        )
        for label, val in [("Opacity 80%",0.80),("Opacity 90%",0.90),("Opacity 100%",1.00)]:
            a = QAction(label, self)
            a.triggered.connect(lambda _, v=val: self.setWindowOpacity(v))
            menu.addAction(a)
        menu.addSeparator()
        qa = QAction("Quit", self); qa.triggered.connect(QApplication.quit)
        menu.addAction(qa)
        menu.exec_(e.globalPos())


def run_overlay(state_queue: "_queue.Queue"):
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("RL Coach")
    w = RLCoachOverlay(state_queue)
    w.show()
    app.exec_()
