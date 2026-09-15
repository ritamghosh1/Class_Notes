# Dashboard Module Theory — `dashboard.py`

> **File**: `dashboard.py`  
> **Role**: Live terminal visualization  
> **Layer**: UI / Presentation

---

## 1. What This Module Does

`dashboard.py` provides a **Rich-based live terminal dashboard** that visualizes the simulation state in real time. It uses the [Rich](https://rich.readthedocs.io/) library to render a structured, color-coded layout that updates at 8 FPS.

This is a **scope extra** — it goes beyond what the assignment requires to provide an extraordinary presentation-ready demo.

---

## 2. Dashboard Layout

```
╔══════════════════════════════════════════════════════════════╗
║  CSMA Simulator — CSMA_CD  |  Stations: 8  |  t = 452      ║  ← Header
╠══════════════════════╦═══════════════════════════════════════╣
║  Channel State       ║  Live Metrics                        ║
║  ● BUSY              ║    Collisions      : 23              ║
╠══════════════════════║    Frames Sent     : 156             ║
║  Stations (8)        ║    Throughput      : 0.3467          ║
║   0  TRANSMITTING ▶  ║    Utilization     : 45.2%           ║
║   1  IDLE         ●  ║    Collision Rate  : 5.1%            ║
║   2  WAITING      ◌  ║    Sim Time        : 452 slots       ║
║   3  IDLE         ●  ║    Progress        : 45.2%           ║
║   4  TRANSMITTING ▶  ╠═══════════════════════════════════════╣
║   5  DONE         ✓  ║  Event Log                           ║
║   6  WAITING      ◌  ║  [t=451] Stn  0: TRANSMIT frame=12  ║
║   7  IDLE         ●  ║  [t=451] Stn  4: TRANSMIT frame=8   ║
╠══════════════════════║  [t=452] COLLISION: stations [0, 4]  ║
║  Sparklines          ║  [t=452] Stn  0: BACKOFF k=2        ║
║  Collision: ▁▂▃▅▆▇█▅ ║  [t=452] Stn  4: BACKOFF k=1        ║
║  Throughput: ▅▆▇▇▆▅▄ ║                                      ║
╠══════════════════════╩═══════════════════════════════════════╣
║  [████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 45%   ║  ← Progress
╚══════════════════════════════════════════════════════════════╝
```

---

## 3. Components

### Channel State Panel
Shows the current channel state with **color coding**:
- 🟢 **Green**: IDLE — channel is free
- 🔵 **Cyan**: BUSY — one station transmitting
- 🔴 **Red**: COLLISION — two or more stations collided

### Station Grid
A table showing each station's current state:

| Symbol | Color | Meaning |
|--------|-------|---------|
| `●` | Green | IDLE — ready to sense/transmit |
| `◉` | Yellow | SENSING — checking channel |
| `▶` | Cyan | TRANSMITTING — frame in flight |
| `◌` | Yellow | WAITING — backing off |
| `✓` | Dim | DONE — all frames sent |

### Sparkline Charts
Unicode sparklines (using `▁▂▃▄▅▆▇█` characters) showing rolling trends:
- **Collision Rate**: Red sparkline showing recent collision frequency
- **Throughput**: Cyan sparkline showing recent throughput

### Metrics Panel
Numeric display of key performance metrics updated live.

### Event Log
Scrolling log of the last 15 events (color-coded):
- **Cyan**: TRANSMIT events
- **Yellow**: DEFER events
- **Red**: COLLISION events

---

## 4. Thread Safety

The dashboard runs on Rich's `Live` renderer which uses a background thread for display updates. All state mutations are protected by `threading.Lock()` to prevent data races between the simulation loop (writing) and the renderer (reading).

---

## 5. NullDashboard Pattern

When `--dashboard` is not specified, the simulation uses `NullDashboard` — a no-op class that silently ignores all method calls. This avoids cluttering the simulation code with `if dashboard:` checks everywhere:

```python
class NullDashboard:
    def start(self): pass
    def stop(self): pass
    def update(self, *args, **kwargs): pass
    def log_collision(self, *args, **kwargs): pass
```

---

## 6. Dependencies

- **Required**: `rich` library (`pip install rich`)
- **Fallback**: If `rich` is not installed, the dashboard gracefully falls back to `NullDashboard` with a warning message
