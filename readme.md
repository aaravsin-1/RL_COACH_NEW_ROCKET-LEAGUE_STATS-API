# RL COACH
### Real-Time Opponent Intelligence & Self-Analysis for Rocket League

---

## What is it?

RL Coach is a Python application that runs alongside Rocket League and connects to the game's official Stats API. It reads every match event in real time — goals, touches, demos, ball hits, saves — and displays a semi-transparent overlay directly over your game showing:

- Live analysis of every opponent with coaching tips on how to beat them
- Your own performance metrics, efficiency tracking, and session record
- A post-match report after every game with strengths, weaknesses, decision audit, and specific training drills

Everything persists between sessions. The more you play, the smarter it gets.

---

## Requirements

- Windows 10 / 11
- Python 3.10+
- Rocket League (Epic Games, post-April 2026 update with native Stats API)
- PyQt5

```bash
pip install PyQt5
```

---

## Setup (one time only)

### Step 1 — Enable the Stats API in Rocket League

Rocket League must be fully closed before editing this file.

Open:
```
C:\Users\<YourName>\Documents\My Games\Rocket League\TAGame\Config\DefaultStatsAPI.ini
```

Replace the entire contents with:
```ini
[TAGame.MatchStatsExporter_TA]

; Port the client will listen for connections on
Port=49123

; How many times per second the game sends the update state (capped at 120, 0 disables this feature)
PacketSendRate=20
```

Save it. The `[TAGame.MatchStatsExporter_TA]` section header is required — `[API]` will not work.

> **Important:** The port (49123) only opens once you are inside an active match. It will not be open in menus, training, or the lobby. Run `netstat -ano | findstr 49123` while in a live match to confirm it shows `LISTENING`.

### Step 2 — Set your in-game name

Open `config.py` and set your exact Rocket League display name:

```python
LOCAL_PLAYER_NAME = "dogmiv"
```

This tells the system which player is you so it tracks your stats separately from opponents.

### Step 3 — Run

```bash
python main.py
```

The overlay appears immediately in the top-right corner of your screen. It will show `● WAITING` until you enter a match, then switch to `● LIVE` automatically.

Open Rocket League, queue into any match, and the overlay activates the moment the match begins.

---

## File structure

```
rl_coach/
├── main.py                      Entry point. Starts overlay + TCP client.
├── config.py                    All settings — edit this to customise.
├── session.py                   Routes game events, manages match state.
├── ws_client.py                 Raw TCP client. Connects to RL Stats API.
│
├── models/
│   ├── player_profile.py        Persistent opponent data model.
│   ├── live_state.py            Per-match live player state + metrics.
│   ├── match_state.py           Current match metadata (teams, score, timer).
│   ├── self_profile.py          Your persistent profile across all matches.
│   └── session_record.py        Single completed match record.
│
├── engine/
│   ├── analysis_engine.py       Computes live metrics from raw state.
│   ├── coaching_engine.py       Generates prioritised tips per opponent.
│   ├── decision_audit.py        Touch → outcome timeline analysis.
│   ├── motivator.py             Contextual motivational messages.
│   ├── training_engine.py       Maps weak metrics to specific drills.
│   └── post_match_engine.py     Builds the full post-match report.
│
├── storage/
│   ├── player_db.py             Loads/saves opponent profiles to JSON.
│   └── self_db.py               Loads/saves your profile + match history.
│
├── overlay/
│   └── app.py                   PyQt5 overlay — all UI code lives here.
│
└── data/
    ├── players.json             Opponent profile database. Grows each match.
    ├── self_profile.json        Your persistent profile.
    └── match_history.json       Full history of every match you've played.
```

---

## Configuration reference

All settings are in `config.py`. Edit this file to customise behaviour.

| Setting | Default | Description |
|---|---|---|
| `LOCAL_PLAYER_NAME` | `"dogmiv"` | Your exact in-game display name |
| `GAME_MODE` | `"2v2"` | Your main mode — affects coaching tip tuning |
| `RL_WS_HOST` | `"127.0.0.1"` | RL Stats API host — do not change |
| `RL_WS_PORT` | `49123` | Must match Port in DefaultStatsAPI.ini |
| `UI_SCALE` | `1.0` | Overlay size multiplier. 1.5 = 50% bigger |
| `EMA_ALPHA` | `0.25` | How fast profiles update. Higher = new matches matter more |
| `SESSION_WINDOW_HOURS` | `4` | Matches within this window count as one session |
| `AUDIT_WINDOW_SECS` | `12.0` | Seconds after your touch to check for goals |
| `CONFIDENCE_LOW` | `1` | Matches needed for Low confidence rating |
| `CONFIDENCE_MED` | `5` | Matches needed for Medium confidence rating |
| `CONFIDENCE_HIGH` | `12` | Matches needed for High confidence rating |
| `TILT_EFF_DROP` | `0.15` | Efficiency drop threshold to trigger tilt warning |
| `TILT_WINDOW` | `3` | Matches to look back for tilt detection |

### Scaling the overlay

If the overlay feels too small, change `UI_SCALE` in `config.py`:

```python
UI_SCALE = 1.0   # default
UI_SCALE = 1.3   # 30% bigger
UI_SCALE = 1.5   # 50% bigger — recommended for 1440p
UI_SCALE = 1.8   # 80% bigger — recommended for 4K
```

Restart `main.py` after changing it.

---

## The overlay — full breakdown

### Title bar
```
RL COACH  ● LIVE                    DB:47  –  ×
```
- `● LIVE` (green) — connected and receiving data from an active match
- `● WAITING` (grey) — connected but no match in progress
- `DB:47` — number of opponent profiles stored in your database
- `–` — collapse to match bar only
- `×` — quit

### Match bar
```
BLUE   1  ——  3:42  ——  2   ORANGE
```
Always visible even when collapsed. Shows team names (colour-coded to in-game team colours), live scores, and the match countdown. The clock continues ticking locally even if your network drops packets — it interpolates based on the last known value rather than freezing.

Shows `OVERTIME` in gold during overtime and `🏆 BLUE WIN` in green when a winner is decided.

### Opponent cards

One card per opponent. In 2v2 you see 2 cards. Each card has five sections:

#### 1. Header
```
PlayerName    BALL-CHASER    Diamond/Champ    ●
```
- **Name** — their display name
- **Playstyle tag** — see playstyle section below
- **Rank estimate** — rough tier based on efficiency and consistency signals
- **Confidence dot** — grey = first encounter, amber = some data, green = 12+ matches (highly reliable). Hover for exact count.

A deviation badge appears when they're playing differently to their history:
```
▲ MORE AGGRESSIVE THAN USUAL
▼ MORE PASSIVE THAN USUAL
```

#### 2. Stats row
```
G    SH    SV    TCH    DM    ACC
1     5     0     35     2    20%
```
- **G** — goals this match
- **SH** — shot attempts
- **SV** — saves
- **TCH** — total ball touches
- **DM** — demos inflicted
- **ACC** — shot accuracy (goals / shots). Green = 50%+, amber = 25–50%, red = below 25%

#### 3. Meter bars
Three paired bars showing the live current-match value:

```
AGG  ████████░░  80%
EFF  ████░░░░░░  38%
RSK  ██████████  100%
```

| Metric | What it measures | Formula |
|---|---|---|
| AGG | How actively they challenge and hunt the ball | (touches/min ÷ 8)×0.4 + (shots/min ÷ 1.5)×0.4 + (demos/min ÷ 0.4)×0.2 |
| EFF | Value produced per touch | (goals×3 + shots×0.5 + assists×2 + saves×2) ÷ touches ÷ 0.7 |
| RSK | How much they're gambling | (demos/min ÷ 0.4)×0.7 + (1 − shot accuracy)×0.3 |

**Calibrated benchmarks:**
| Player type | AGG | EFF | RSK |
|---|---|---|---|
| Ball-chaser | 0.87 | 0.12 | 1.00 |
| Aggressive-Efficient | 0.67 | 0.74 | 0.47 |
| Average 2v2 player | 0.34 | 0.67 | 0.20 |
| Calculated-Passive | 0.20 | 0.90 | 0.15 |
| Passive | 0.13 | 0.09 | 0.30 |

#### 4. Deviation badge
Only appears once you have Medium or High confidence on a player. Compares their live aggression against their historical average. A 20%+ gap triggers the badge.

#### 5. Coaching tips
Up to 3 tips, colour-coded by urgency:

| Colour | Icon | Meaning |
|---|---|---|
| Red | ⚡ | Act on this immediately |
| Amber | ⚠ | Important pattern |
| Cyan | · | Useful context |

Example tips the system generates:
- ⚡ `Ball-chaser — FAKE CHALLENGE. They will always commit first.`
- ⚡ `Extremely aggressive right now — hang back, let them overextend.`
- ⚠ `Playing MORE aggressive than usual (normally 34% → now 72%).`
- ⚠ `Demo-hungry — dodge sideways after clears, don't drive straight.`
- ⚠ `Wasting boost — time your challenges when they're likely empty.`
- · `High accuracy (67%) — do NOT leave net exposed.`
- · `First time seeing this player. Tips improve each match.`

### Your panel
```
YOU: dogmiv                    W3   2W-1L TODAY
G:1   SH:3   SV:1   TCH:18   BST:60%
EFF  ██████░░░░  62%
"3 win streak. Efficiency 67% — above your average. Ride this."
```
- Your live stats this match
- Boost level — green (60%+), amber (25–60%), red (below 25%)
- Your efficiency bar for this match
- Current streak — green for win streak, red for loss streak
- Today's session record
- Motivator quote from your last completed match

---

## Post-match report

Appears automatically in the centre of your screen for 50 seconds after every match. Drag it to reposition. Click `×` to dismiss early.

### Result and score
```
WIN   2 – 1   ·   5:12
```
WIN or LOSS in large text, score, and actual match duration.

### Motivator message
A single specific message based on your actual situation. Not generic. Examples:

- *"5 wins in a row. You're locked in — don't start gambling now. Keep the reads clean."*
- *"Down 3 in a row. Your efficiency dropped each game — this is recoverable. Take a breath."*
- *"Loss but you played above your average (71% vs 65%). That's a good loss — keep queuing."*
- *"Your efficiency has dropped across the last 3 games. This is a tilt pattern. Take 10 minutes before queuing again."*
- *"You made 2 saves — the defence was there. Goals need more looks."*

### Strengths
Up to 3 things that actually went well this match, based on your numbers:
- *"Shot accuracy 100% — converting looks well."*
- *"2 saves — solid defensive positioning."*
- *"Efficiency above your average — cleaner touches than usual."*
- *"Multiple positive touch sequences — good decision-making."*

### Weaknesses
Up to 3 specific things to fix:
- *"Shot accuracy only 18% — wait for better looks."*
- *"Efficiency 20% below your avg 50% — low value touches."*
- *"Boost wasted — burning without enough speed output."*
- *"3 touches led to conceded goals — watch overcommitting."*

### Decision audit
The closest thing to a replay analyser without video. Every time you hit the ball, the system checks what happened within 12 seconds. Each goal credits or blames one touch — the most recent touch before that goal. No duplicates.

- *"⚠ [4:55] Your touch at 4:55 remaining led to a conceded goal within 12s — possible overcommit."*
- *"✓ [1:55] Your touch at 1:55 remaining contributed to a goal within 12s — good read."*
- *"📊 19% of your touches led to conceded goals — focus on touch quality over quantity."*

### Training prescriptions
2 drill recommendations auto-generated from your weakest metrics this match:

**Boost Management** (15 min)
*Burning boost without sufficient speed output.*
Low-boost free play (cap yourself at 33 boost)  |  Boost pad routing

**Touch Quality** (20 min)
*Touches aren't producing enough value — too many neutral touches.*
Dribbling + carry → shot combo drills  |  Wall play workshop maps

**2v2 Rotations** (20 min)
*High risk score suggests overcommitting or double-committing in 2s.*
Shadowing drill with a partner  |  Watch your own replays: mark every double-commit

---

## Playstyle classifications

| Classification | AGG | EFF | What it means | Counter-strategy |
|---|---|---|---|---|
| **Ball-Chaser** | 0.65+ | below 0.40 | Constantly challenges, rarely converts | Fake challenge — they commit every time. Take the free ball. |
| **Aggressive-Efficient** | 0.65+ | 0.40+ | Challenges hard and converts well | Only challenge when you have a clear advantage. Match their tempo. |
| **Calculated-Passive** | below 0.30 | 0.50+ | Waits for opportunities, efficient when active | Apply constant pressure. They'll sit back — don't let them reset. |
| **Passive** | below 0.30 | below 0.50 | Low involvement, low conversion | Focus on your own rotations. They're not a real threat. |
| **Balanced** | 0.30–0.65 | any | Neither extreme | Read their live meters as the match develops. |

---

## How the learning system works

### Opponent profiles
Every opponent you face gets a profile stored in `data/players.json` keyed by their platform ID (`Steam|123|0`). Name changes never lose their history.

After each match, behavioural metrics update using EMA (Exponential Moving Average) with α=0.25:
```
new_value = 0.75 × old_value + 0.25 × this_match_value
```
This means recent matches count more than old ones, but history never fully vanishes. After 12+ matches the profile is considered highly reliable and tips become very specific.

### Your own profile
Your counting stats (goals, saves, touches, score) use a true running average — so after 2 matches with 2 goals each, your `avg_goals` is exactly 2.0.

Your behavioural metrics (aggression, efficiency, risk) use EMA so your "normal" reflects recent form, not games from months ago.

### Confidence levels

| Level | Matches seen | What it means |
|---|---|---|
| None (grey dot) | 0 | First encounter. Tips are generic archetypes only. |
| Low (dim amber) | 1–4 | Early data. Treat tips as preliminary. |
| Medium (amber) | 5–11 | Reliable patterns forming. Deviation detection activates. |
| High (green dot) | 12+ | Strong baseline. Tips are highly specific to this player. |

### Session tracking
Matches within `SESSION_WINDOW_HOURS` (default 4 hours) count as the same session. Your TODAY record and session win rate reset when you come back after a break. Tilt detection looks across the last 3 matches in the current session.

---

## Accuracy — honest assessment

### High confidence (exact data from RL)
- Goals, shots, saves, touches, demos, assists — exact
- Match score and clock — exact
- Win/loss result — exact
- Shot accuracy — exact

### Medium confidence (good approximation)
- **Aggression/Efficiency/Risk scores** — calibrated against real 2v2 archetypes and directionally accurate, but there is no ground truth to validate against. They correctly distinguish ball-chasers from passive players, but the exact percentage numbers should be read as relative indicators, not absolute measurements.
- **Playstyle classification** — reliable for clear archetypes (a true ball-chaser will always show high AGG, low EFF). Less reliable for players near the Balanced threshold.
- **Decision audit** — correlational, not causal. "Your touch → goal 8 seconds later" is a flag, not proof you caused it. A teammate's touch between yours and the goal would not be captured without positional data.

### Low confidence (rough approximation)
- **Boost efficiency** — only available when you are spectating or it's your own team. For opponents in normal play, this field is not provided by the API and defaults to 0.5.
- **Estimated rank** — a heuristic based on efficiency and consistency. Useful for rough clustering (definitely Diamond vs definitely Bronze) but will misclassify mid-tier players regularly. Not your actual MMR.

### What it cannot do
- See player positions — the API provides no coordinate data
- Know who is in net vs attacking — no positional data
- Detect mechanics like air dribbles or flip resets — only outcome stats
- Track replays of old matches — only live active matches
- Guarantee tips are correct — they are pattern-based rules, not a neural network

---

## Network resilience

The system handles bad network conditions in three ways:

**Queue design** — The internal queue is `maxsize=1`. The session always replaces stale data with the latest snapshot. The overlay drains the entire queue each poll cycle. You will never see the overlay "catch up" through old game states after a freeze — it always jumps straight to current.

**Clock interpolation** — A local 1-second timer keeps the match clock ticking even when packets stop arriving. If your connection drops for 10 seconds, the clock counts down locally rather than freezing.

**Packet bursts** — RL sometimes sends 20 updates in one second followed by silence. The queue handles this gracefully — the overlay processes the burst and renders only the latest state, with no backlog.

---

## Controls

| Action | Result |
|---|---|
| Drag anywhere on overlay | Move the overlay |
| `–` button | Collapse to match bar only |
| Middle-click | Toggle collapse |
| Right-click | Opacity menu: 80% / 90% / 100% |
| `×` button | Quit RL Coach |

---

## Persistent data

All data is stored in the `data/` folder.

| File | Contents |
|---|---|
| `data/players.json` | All opponent profiles. Grows every match. |
| `data/self_profile.json` | Your profile — averages, streak, all-time record. |
| `data/match_history.json` | Every match you've played, with full report data. |

To reset everything, delete the contents of the `data/` folder. To reset only your own profile, delete `self_profile.json` and `match_history.json`. To keep your own data but reset opponent profiles, delete `players.json`.

---

## Logs

A log file `rl_coach.log` is created in the project folder. It records connections, disconnections, player tracking events, and match results. If something isn't working, check this file first.

---

## Troubleshooting

**Overlay shows `● WAITING` even when in a match**
- Confirm the Stats API ini uses `[TAGame.MatchStatsExporter_TA]` (not `[API]`)
- Run `netstat -ano | findstr 49123` while in an active match — it must show `LISTENING`
- Fully restart Rocket League after editing the ini file

**Port shows `SYN_SENT` but never `LISTENING`**
- You are not in an active match. The port only opens once the ball spawns and gameplay begins — not in menus, not in the lobby countdown

**My name isn't being detected**
- Open `config.py` and make sure `LOCAL_PLAYER_NAME` matches your display name exactly, including capitalisation

**Overlay is too small**
- Increase `UI_SCALE` in `config.py`. Start at `1.5` for 1440p monitors.

**Post-match popup doesn't appear**
- It only appears when a full match ends via `MatchEnded` event. Leaving mid-match or playing private matches that don't fire this event will not trigger the popup.

**Clock froze during match**
- Fixed in current version. Clock now interpolates locally when packets stop arriving. If still occurring, check your `rl_coach.log` for disconnect/reconnect messages.