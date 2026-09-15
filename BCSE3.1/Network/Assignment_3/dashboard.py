"""
dashboard.py
============
Rich-based live terminal dashboard for CSMA protocol simulation.

Provides real-time visual feedback during simulation:
  - Channel state indicator (IDLE / BUSY / COLLISION) with color
  - Station status grid (color-coded per station state)
  - Live metrics panel (collisions, throughput, utilization)
  - Collision-rate sparkline chart
  - Throughput sparkline chart
  - Scrolling event log
  - Simulation progress bar

Usage:
    from dashboard import Dashboard, NullDashboard

    dash = Dashboard(protocol="csma_cd", num_stations=8, total_frames=400)
    dash.start()
    ...
    dash.update(current_time, slot, total_slots, stations, channel, events)
    dash.log_collision(time, station_ids)
    ...
    dash.stop()

Requires:
    pip install rich
"""

from __future__ import annotations

import time
import threading
from collections import deque

try:
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.progress_bar import ProgressBar
    from rich.console import Console
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ---------------------------------------------------------------------------
# Sparkline renderer
# ---------------------------------------------------------------------------

_SPARK = "▁▂▃▄▅▆▇█"


def _sparkline(values: list | deque, width: int = 40) -> str:
    """Render a Unicode sparkline from numeric values."""
    if not values:
        return ""
    vals = list(values)[-width:]
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1.0
    return "".join(
        _SPARK[min(int((v - mn) / rng * (len(_SPARK) - 1)), len(_SPARK) - 1)]
        for v in vals
    )


# ---------------------------------------------------------------------------
# State → color / symbol mapping
# ---------------------------------------------------------------------------

_CHANNEL_COLORS = {
    "IDLE":      "green",
    "BUSY":      "cyan",
    "COLLISION": "bold red",
}

_STATION_COLORS = {
    "IDLE":         ("green",  "●"),
    "SENSING":      ("yellow", "◉"),
    "TRANSMITTING": ("cyan",   "▶"),
    "WAITING":      ("yellow", "◌"),
    "DONE":         ("dim",    "✓"),
}


# ---------------------------------------------------------------------------
# Dashboard class
# ---------------------------------------------------------------------------

class Dashboard:
    """
    Live terminal dashboard for CSMA simulation monitoring.

    Thread-safe: every state mutation is protected by a lock.
    """

    def __init__(self,
                 protocol: str,
                 num_stations: int,
                 total_frames: int):
        if not HAS_RICH:
            raise ImportError(
                "Dashboard requires 'rich'. Install: pip install rich"
            )

        self.protocol       = protocol
        self.num_stations   = num_stations
        self.total_frames   = total_frames

        # Live data (protected by lock)
        self._lock          = threading.Lock()
        self._current_time  = 0.0
        self._progress      = 0.0
        self._channel_state = "IDLE"
        self._collisions    = 0
        self._frames_sent   = 0
        self._throughput    = 0.0
        self._utilization   = 0.0
        self._collision_rate= 0.0

        # Station states: [(state_name, ...)]
        self._station_states: list[str] = ["IDLE"] * num_stations

        # Sparkline data
        self._collision_history: deque[float] = deque(maxlen=60)
        self._throughput_history: deque[float] = deque(maxlen=60)

        # Event log
        self._log_entries: deque[tuple[str, str]] = deque(maxlen=30)

        # Rich Live
        self._console = Console()
        self._live: Live | None = None

    def start(self) -> None:
        """Start the live dashboard."""
        self._live = Live(
            self._build_layout(),
            console=self._console,
            refresh_per_second=8,
            screen=False,
        )
        self._live.start()

    def stop(self) -> None:
        """Stop the live dashboard."""
        if self._live:
            self._live.stop()

    def reset(self, new_protocol: str = None) -> None:
        """Reset the dashboard state for a new simulation run."""
        with self._lock:
            if new_protocol:
                self.protocol = new_protocol
            self._current_time  = 0.0
            self._progress      = 0.0
            self._channel_state = "IDLE"
            self._collisions    = 0
            self._frames_sent   = 0
            self._throughput    = 0.0
            self._utilization   = 0.0
            self._collision_rate= 0.0
            self._station_states = ["IDLE"] * self.num_stations
            self._collision_history.clear()
            self._throughput_history.clear()
            self._log_entries.clear()

    # ------------------------------------------------------------------
    # State update (called from simulation loop)
    # ------------------------------------------------------------------

    def update(self, current_time, slot, total_slots, stations, channel, events):
        """Update dashboard with latest simulation state."""
        with self._lock:
            self._current_time = current_time
            self._progress = slot / max(total_slots, 1)
            self._channel_state = channel.state.name
            self._collisions = channel.stats["total_collisions"]
            self._frames_sent = sum(s.metrics["frames_sent"] for s in stations)
            self._throughput = self._frames_sent / max(slot, 1)
            self._utilization = channel.get_utilization(max(slot, 1))
            self._collision_rate = channel.get_collision_rate(max(slot, 1))

            # Update station states
            for i, s in enumerate(stations):
                if i < len(self._station_states):
                    self._station_states[i] = s.state.name

            # Sparklines
            self._collision_history.append(self._collision_rate)
            self._throughput_history.append(self._throughput)

            # Log events
            for ev in events:
                style = "white"
                if ev.action == "COLLISION":
                    style = "bold red"
                elif ev.action == "TRANSMIT":
                    style = "cyan"
                elif ev.action == "DEFER":
                    style = "yellow"
                self._log_entries.append((str(ev), style))

        # Refresh display
        if self._live:
            self._live.update(self._build_layout())

    def log_collision(self, current_time, station_ids):
        """Log a collision event."""
        with self._lock:
            msg = f"[t={current_time:.0f}] 💥 COLLISION: stations {station_ids}"
            self._log_entries.append((msg, "bold red"))

    def log(self, msg: str, style: str = "white"):
        """Add a message to the event log."""
        with self._lock:
            self._log_entries.append((msg, style))

    # ------------------------------------------------------------------
    # Layout building
    # ------------------------------------------------------------------

    def _build_layout(self) -> Layout:
        """Build the complete dashboard layout."""
        layout = Layout()

        layout.split_column(
            Layout(name="header",  size=3),
            Layout(name="body",    ratio=1),
            Layout(name="footer",  size=3),
        )

        # Header
        layout["header"].update(
            Panel(
                Text(f"  CSMA Simulator — {self.protocol.upper()}  "
                     f"|  Stations: {self.num_stations}  "
                     f"|  t = {self._current_time:.0f}",
                     style="bold white"),
                style="blue",
                box=box.HEAVY,
            )
        )

        # Body: split into left and right
        layout["body"].split_row(
            Layout(name="left",  ratio=1),
            Layout(name="right", ratio=1),
        )

        # Left: channel + stations + sparklines
        layout["left"].split_column(
            Layout(name="channel_panel", size=5),
            Layout(name="station_grid",  ratio=1),
            Layout(name="sparklines",    size=8),
        )

        # Right: metrics + event log
        layout["right"].split_column(
            Layout(name="metrics",   size=12),
            Layout(name="event_log", ratio=1),
        )

        # ---- Channel state ----
        ch_color = _CHANNEL_COLORS.get(self._channel_state, "white")
        ch_text = Text(f"  ● {self._channel_state}", style=ch_color)
        layout["channel_panel"].update(
            Panel(ch_text, title="Channel State", border_style=ch_color)
        )

        # ---- Station grid ----
        grid = Table(box=box.SIMPLE, show_header=True, pad_edge=False)
        grid.add_column("Stn", style="dim", width=5)
        grid.add_column("State", width=14)
        grid.add_column("", width=3)

        for i, state in enumerate(self._station_states):
            color, symbol = _STATION_COLORS.get(state, ("white", "?"))
            grid.add_row(
                f" {i:>2}",
                Text(state, style=color),
                Text(symbol, style=color),
            )

        layout["station_grid"].update(
            Panel(grid, title=f"Stations ({self.num_stations})",
                  border_style="blue")
        )

        # ---- Sparklines ----
        collision_spark = _sparkline(self._collision_history)
        throughput_spark = _sparkline(self._throughput_history)
        spark_text = Text()
        spark_text.append("  Collision Rate:  ", style="dim")
        spark_text.append(collision_spark, style="red")
        spark_text.append(f"  {self._collision_rate:.2%}\n", style="red")
        spark_text.append("  Throughput:      ", style="dim")
        spark_text.append(throughput_spark, style="cyan")
        spark_text.append(f"  {self._throughput:.4f}", style="cyan")

        layout["sparklines"].update(
            Panel(spark_text, title="Sparklines", border_style="magenta")
        )

        # ---- Metrics ----
        metrics_table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
        metrics_table.add_column("Metric", style="dim", width=20)
        metrics_table.add_column("Value", width=20)

        metrics_data = [
            ("Collisions",      f"{self._collisions}"),
            ("Frames Sent",     f"{self._frames_sent}"),
            ("Throughput",      f"{self._throughput:.4f}"),
            ("Utilization",     f"{self._utilization:.2%}"),
            ("Collision Rate",  f"{self._collision_rate:.2%}"),
            ("Sim Time",        f"{self._current_time:.0f} slots"),
            ("Progress",        f"{self._progress:.1%}"),
        ]
        for label, value in metrics_data:
            metrics_table.add_row(f"  {label}", value)

        layout["metrics"].update(
            Panel(metrics_table, title="Live Metrics", border_style="green")
        )

        # ---- Event log ----
        log_text = Text()
        with self._lock:
            for msg, style in list(self._log_entries)[-15:]:
                log_text.append(msg + "\n", style=style)

        layout["event_log"].update(
            Panel(log_text, title="Event Log", border_style="yellow")
        )

        # Footer: progress bar
        pct = int(self._progress * 100)
        bar = f"{'█' * (pct // 2)}{'░' * (50 - pct // 2)}"
        layout["footer"].update(
            Panel(
                Text(f"  [{bar}] {pct}%", style="bold green"),
                style="dim",
            )
        )

        return layout


# ---------------------------------------------------------------------------
# NullDashboard — fallback when --dashboard is not specified
# ---------------------------------------------------------------------------

class NullDashboard:
    """No-op dashboard that silently ignores all calls."""
    def start(self): pass
    def stop(self): pass
    def reset(self, *args, **kwargs): pass
    def update(self, *args, **kwargs): pass
    def log_collision(self, *args, **kwargs): pass
    def log(self, *args, **kwargs): pass


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  Dashboard Module — Self-Test")
    print("=" * 60)

    # Test 1: NullDashboard works without errors
    nd = NullDashboard()
    nd.start()
    nd.update(0, 0, 100, [], None, [])
    nd.log("test message")
    nd.log_collision(0, [1, 2])
    nd.stop()
    print("[1] NullDashboard operates silently         ✓")

    # Test 2: Sparkline rendering
    data = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0, 0.8, 0.6, 0.4, 0.2]
    spark = _sparkline(data)
    assert len(spark) == len(data)
    print(f"[2] Sparkline: {spark}                      ✓")

    # Test 3: Check Rich availability
    if HAS_RICH:
        print("[3] Rich library is available               ✓")
        # Quick instantiation test (without starting)
        d = Dashboard(protocol="csma_cd", num_stations=4, total_frames=100)
        assert d.num_stations == 4
        print("[4] Dashboard instantiation                 ✓")
    else:
        print("[3] Rich not installed (dashboard disabled) ⚠")
        print("[4] Skipped (Rich required)                 ⚠")

    print()
    print("All dashboard self-tests passed ✅")
    print("=" * 60)
