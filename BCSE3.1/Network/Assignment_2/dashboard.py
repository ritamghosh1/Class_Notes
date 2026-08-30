"""
dashboard.py
============
Rich-based live terminal dashboard for ARQ protocol visualization.

Provides real-time visual feedback during protocol execution:
  - Sliding window state with colored frame slots
  - RTT / RTO sparkline chart
  - Live metrics (efficiency, throughput, retransmissions)
  - Scrolling event log

Usage:
    from dashboard import Dashboard, NullDashboard

    dash = Dashboard(protocol="gbn", window_size=4, total_frames=100,
                     host="192.168.1.5", port=5001, role="SENDER")
    dash.start()
    ...
    dash.frame_sent(idx=0)
    dash.frame_acked(idx=0)
    dash.update_rtt(sample_rtt=31.2, srtt=30.5, rto=150.0)
    ...
    dash.stop()

Requires:
    pip install rich
"""

from __future__ import annotations

import time
import threading
from collections import deque
from enum import IntEnum

try:
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.console import Console
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ---------------------------------------------------------------------------
# Frame state enum
# ---------------------------------------------------------------------------

class FrameStatus(IntEnum):
    NOT_SENT = 0
    SENT     = 1   # In flight, waiting for ACK
    ACKED    = 2   # Successfully acknowledged
    TIMEOUT  = 3   # Timer expired, pending retransmit
    NAK      = 4   # NAK received, pending retransmit


# ---------------------------------------------------------------------------
# Sparkline renderer
# ---------------------------------------------------------------------------

_SPARK = "▁▂▃▄▅▆▇█"


def _sparkline(values: list | deque, width: int = 35) -> str:
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
# Dashboard — Rich live terminal UI
# ---------------------------------------------------------------------------

class Dashboard:
    """
    Live terminal dashboard for ARQ protocol monitoring.

    Thread-safe: every state mutation is protected by a lock.
    """

    def __init__(self,
                 protocol: str,
                 window_size: int,
                 total_frames: int,
                 host: str,
                 port: int,
                 role: str = "SENDER"):
        if not HAS_RICH:
            raise ImportError(
                "Rich library is required for the dashboard.  Install with:\n"
                "    pip install rich"
            )

        self.protocol     = protocol.upper()
        self.window_size  = window_size
        self.total_frames = max(total_frames, 1)
        self.host         = host
        self.port         = port
        self.role         = role.upper()

        # ---- Thread safety ------------------------------------------------
        self._lock = threading.Lock()

        # ---- Sender state -------------------------------------------------
        self._frame_states: dict[int, FrameStatus] = {}
        self._base     = 0
        self._next_idx = 0

        self._frames_sent          = 0
        self._frames_retransmitted = 0
        self._frames_original      = 0
        self._data_bytes           = 0
        self._start_time           = time.time()

        # RTT
        self._rtt_samples: deque[float] = deque(maxlen=60)
        self._rto_history: deque[float] = deque(maxlen=60)
        self._srtt = 0.0
        self._rto  = 0.0

        # ---- Receiver state -----------------------------------------------
        self._frames_received  = 0
        self._frames_accepted  = 0
        self._frames_discarded = 0
        self._acks_sent        = 0
        self._naks_sent        = 0
        self._buffer_size      = 0
        self._recv_expected    = 0

        # ---- Event log ----------------------------------------------------
        self._events: deque[tuple[str, str, str]] = deque(maxlen=22)

        # ---- Rich console / live display ----------------------------------
        self._console = Console()
        self._live: Live | None = None

    # ======================================================================
    # Lifecycle
    # ======================================================================

    def start(self) -> None:
        """Start the live dashboard."""
        self._start_time = time.time()
        self._live = Live(
            self._render(),
            console=self._console,
            refresh_per_second=8,
            screen=False,
        )
        self._live.start()

    def stop(self) -> None:
        """Stop the live dashboard (one final render)."""
        if self._live:
            self._live.update(self._render())
            self._live.stop()
            self._live = None

    def _refresh(self) -> None:
        if self._live:
            try:
                self._live.update(self._render())
            except Exception:
                pass   # swallow transient render errors

    # ======================================================================
    # State-update methods — SENDER
    # ======================================================================

    def frame_sent(self, idx: int) -> None:
        with self._lock:
            self._frame_states[idx] = FrameStatus.SENT
            self._frames_sent += 1
            self._next_idx = max(self._next_idx, idx + 1)
        self._refresh()

    def frame_acked(self, idx: int) -> None:
        with self._lock:
            self._frame_states[idx] = FrameStatus.ACKED
        self._refresh()

    def frame_timeout(self, idx: int) -> None:
        with self._lock:
            self._frame_states[idx] = FrameStatus.TIMEOUT
        self._refresh()

    def frame_retransmit(self, idx: int) -> None:
        with self._lock:
            self._frame_states[idx] = FrameStatus.SENT
            self._frames_retransmitted += 1
        self._refresh()

    def update_window(self, base: int, next_idx: int) -> None:
        with self._lock:
            self._base     = base
            self._next_idx = next_idx
        self._refresh()

    def update_rtt(self, sample_rtt: float, srtt: float, rto: float) -> None:
        with self._lock:
            self._rtt_samples.append(sample_rtt)
            self._rto_history.append(rto)
            self._srtt = srtt
            self._rto  = rto
        self._refresh()

    def update_metrics(self, original: int, retransmitted: int,
                       data_bytes: int) -> None:
        with self._lock:
            self._frames_original      = original
            self._frames_retransmitted = retransmitted
            self._data_bytes           = data_bytes
        self._refresh()

    # ======================================================================
    # State-update methods — RECEIVER
    # ======================================================================

    def recv_frame(self, accepted: bool) -> None:
        with self._lock:
            self._frames_received += 1
            if accepted:
                self._frames_accepted += 1
            else:
                self._frames_discarded += 1
        self._refresh()

    def recv_ack_sent(self) -> None:
        with self._lock:
            self._acks_sent += 1

    def recv_nak_sent(self) -> None:
        with self._lock:
            self._naks_sent += 1

    def recv_buffer_update(self, buf_size: int, expected: int = -1) -> None:
        with self._lock:
            self._buffer_size = buf_size
            if expected >= 0:
                self._recv_expected = expected
        self._refresh()

    # ======================================================================
    # Event log
    # ======================================================================

    def log(self, msg: str, style: str = "") -> None:
        ts = time.strftime("%H:%M:%S")
        with self._lock:
            self._events.append((ts, msg, style))
        self._refresh()

    # ======================================================================
    # Rendering
    # ======================================================================

    def _render(self):
        layout = Layout()

        if self.role == "SENDER":
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="middle", size=9),
                Layout(name="bottom", size=10),
            )
            layout["middle"].split_row(
                Layout(name="window", ratio=3),
                Layout(name="metrics", ratio=2),
            )
            layout["bottom"].split_row(
                Layout(name="rtt", ratio=2),
                Layout(name="log", ratio=3),
            )
            layout["header"].update(self._panel_header())
            layout["window"].update(self._panel_window())
            layout["metrics"].update(self._panel_sender_metrics())
            layout["rtt"].update(self._panel_rtt())
            layout["log"].update(self._panel_log())
        else:   # RECEIVER
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="body"),
            )
            layout["body"].split_row(
                Layout(name="metrics", ratio=2),
                Layout(name="log", ratio=3),
            )
            layout["header"].update(self._panel_header())
            layout["metrics"].update(self._panel_recv_metrics())
            layout["log"].update(self._panel_log())

        return layout

    # ---- Header -----------------------------------------------------------

    def _panel_header(self) -> Panel:
        elapsed = time.time() - self._start_time
        with self._lock:
            base = self._base

        progress = min(base / self.total_frames * 100, 100.0)
        color_map = {"SAW": "red", "GBN": "blue", "SR": "green"}
        color = color_map.get(self.protocol, "white")

        t = Text()
        t.append("  ◉ ", style="bold green")
        t.append(self.protocol, style=f"bold {color}")
        t.append(f" {self.role}", style="bold white")
        arrow = " → " if self.role == "SENDER" else " ← "
        t.append(arrow, style="dim")
        t.append(f"{self.host}:{self.port}", style="dim")
        t.append("  │  ", style="dim")
        t.append(f"{elapsed:.1f}s", style="cyan")
        t.append("  │  ", style="dim")

        # mini progress bar
        bar_w = 20
        filled = int(progress / 100 * bar_w)
        t.append("█" * filled, style=color)
        t.append("░" * (bar_w - filled), style="dim")
        t.append(f" {progress:.0f}%", style="bold")

        return Panel(t, box=box.HEAVY, style=color)

    # ---- Sliding window ---------------------------------------------------

    def _panel_window(self) -> Panel:
        with self._lock:
            base     = self._base
            next_idx = self._next_idx
            states   = dict(self._frame_states)
            ws       = self.window_size
            total    = self.total_frames

        # show ~28 frame slots centred on the current window
        disp = min(28, total)
        lo   = max(0, base - 4)
        hi   = min(total, lo + disp)
        if hi - lo < disp:
            lo = max(0, hi - disp)

        slots = Text()
        nums  = Text()

        for i in range(lo, hi):
            st = states.get(i, FrameStatus.NOT_SENT)
            in_win = base <= i < base + ws

            if st == FrameStatus.ACKED:
                ch, sty = "✓", "bold green"
            elif st == FrameStatus.SENT:
                ch, sty = "▶", "bold cyan"
            elif st == FrameStatus.TIMEOUT:
                ch, sty = "⚡", "bold yellow"
            elif st == FrameStatus.NAK:
                ch, sty = "✗", "bold red"
            else:
                ch, sty = "·", "dim"

            if in_win and st not in (FrameStatus.ACKED,):
                slots.append(f"[{ch}]", style=sty)
            else:
                slots.append(f" {ch} ", style=sty)

            nums.append(f"{i % 256:^3}", style="dim")

        body = Text()
        body.append(f"  base={base}  next={next_idx}  window={ws}\n\n",
                     style="dim italic")
        body.append_text(slots)
        body.append("\n")
        body.append_text(nums)
        body.append("\n\n ")
        body.append(" ✓", style="bold green");  body.append(" ACKed  ", style="dim")
        body.append(" ▶", style="bold cyan");   body.append(" Sent  ", style="dim")
        body.append(" ⚡", style="bold yellow"); body.append(" Timeout  ", style="dim")
        body.append(" ·", style="dim");          body.append(" Pending", style="dim")

        return Panel(body, title="[bold]Sliding Window[/bold]",
                     border_style="cyan", box=box.ROUNDED)

    # ---- Sender metrics ---------------------------------------------------

    def _panel_sender_metrics(self) -> Panel:
        with self._lock:
            orig  = self._frames_original
            retx  = self._frames_retransmitted
            dbytes = self._data_bytes
            base  = self._base

        elapsed  = max(time.time() - self._start_time, 0.001)
        total_tx = orig + retx
        eff      = (orig / total_tx * 100) if total_tx > 0 else 100.0
        tput     = dbytes / elapsed

        tbl = Table(box=None, show_header=False, padding=(0, 1))
        tbl.add_column("M", style="bold", width=14)
        tbl.add_column("V", style="cyan", justify="right")

        tbl.add_row("Frames sent",  str(self._frames_sent))
        tbl.add_row("Original",     str(orig))
        tbl.add_row("Retransmits",  f"[yellow]{retx}[/yellow]")
        tbl.add_row("", "")
        tbl.add_row("Data sent",
                     f"{dbytes/1024:.1f} KB" if dbytes > 1024 else f"{dbytes} B")
        tbl.add_row("Throughput",   f"{tput:.0f} B/s")
        tbl.add_row("", "")
        ec = "green" if eff > 90 else ("yellow" if eff > 70 else "red")
        tbl.add_row("Efficiency",   f"[bold {ec}]{eff:.1f}%[/bold {ec}]")
        tbl.add_row("Progress",     f"{base}/{self.total_frames}")

        return Panel(tbl, title="[bold]Metrics[/bold]",
                     border_style="green", box=box.ROUNDED)

    # ---- RTT / RTO --------------------------------------------------------

    def _panel_rtt(self) -> Panel:
        with self._lock:
            rtts = list(self._rtt_samples)
            rtos = list(self._rto_history)
            srtt = self._srtt
            rto  = self._rto

        body = Text()
        if rtts:
            avg = sum(rtts) / len(rtts)
            body.append("RTT  ", style="bold cyan")
            body.append(_sparkline(rtts), style="cyan")
            body.append(f"  avg={avg:.0f}ms\n", style="dim")

            body.append("RTO  ", style="bold red")
            body.append(_sparkline(rtos), style="red")
            body.append(f"  cur={rto:.0f}ms\n", style="dim")

            body.append("\n ")
            body.append(f"SRTT={srtt:.1f}ms", style="cyan")
            body.append("  │  ", style="dim")
            body.append(f"RTO={rto:.1f}ms", style="red")
            body.append("  │  ", style="dim")
            body.append(f"Samples={len(rtts)}", style="dim")
        else:
            body.append("\n  Waiting for RTT samples …", style="dim italic")

        return Panel(body, title="[bold]RTT / RTO[/bold]",
                     border_style="magenta", box=box.ROUNDED)

    # ---- Receiver metrics -------------------------------------------------

    def _panel_recv_metrics(self) -> Panel:
        with self._lock:
            rcvd = self._frames_received
            acpt = self._frames_accepted
            disc = self._frames_discarded
            acks = self._acks_sent
            naks = self._naks_sent
            buf  = self._buffer_size
            exp  = self._recv_expected

        elapsed = max(time.time() - self._start_time, 0.001)

        tbl = Table(box=None, show_header=False, padding=(0, 1))
        tbl.add_column("M", style="bold", width=16)
        tbl.add_column("V", style="cyan", justify="right")

        tbl.add_row("Frames received",  str(rcvd))
        tbl.add_row("Accepted",         f"[green]{acpt}[/green]")
        tbl.add_row("Discarded (FCS)",  f"[red]{disc}[/red]")
        tbl.add_row("", "")
        tbl.add_row("ACKs sent",        str(acks))
        tbl.add_row("NAKs sent",        f"[yellow]{naks}[/yellow]")
        tbl.add_row("", "")
        tbl.add_row("Buffer size",      str(buf))
        tbl.add_row("Expected seq",     str(exp))
        tbl.add_row("Elapsed",          f"{elapsed:.1f}s")

        return Panel(tbl, title="[bold]Receiver Metrics[/bold]",
                     border_style="green", box=box.ROUNDED)

    # ---- Event log --------------------------------------------------------

    def _panel_log(self) -> Panel:
        with self._lock:
            evts = list(self._events)

        body = Text()
        for ts, msg, sty in evts:
            body.append(f"[{ts}] ", style="dim")
            body.append(f"{msg}\n", style=sty if sty else "white")

        if not evts:
            body.append("  Waiting for events …", style="dim italic")

        return Panel(body, title="[bold]Event Log[/bold]",
                     border_style="yellow", box=box.ROUNDED)


# ---------------------------------------------------------------------------
# NullDashboard — no-op fallback when --dashboard is not used
# ---------------------------------------------------------------------------

class NullDashboard:
    """Silent no-op dashboard; every method is a no-op."""
    def start(self): pass
    def stop(self):  pass
    def frame_sent(self, *a, **kw):         pass
    def frame_acked(self, *a, **kw):        pass
    def frame_timeout(self, *a, **kw):      pass
    def frame_retransmit(self, *a, **kw):   pass
    def update_window(self, *a, **kw):      pass
    def update_rtt(self, *a, **kw):         pass
    def update_metrics(self, *a, **kw):     pass
    def recv_frame(self, *a, **kw):         pass
    def recv_ack_sent(self, *a, **kw):      pass
    def recv_nak_sent(self, *a, **kw):      pass
    def recv_buffer_update(self, *a, **kw): pass
    def log(self, *a, **kw):               pass


# ---------------------------------------------------------------------------
# Self-test — quick visual demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import random

    print("Dashboard self-test — SENDER view (5 seconds) …\n")

    dash = Dashboard(
        protocol="gbn", window_size=4, total_frames=40,
        host="192.168.1.42", port=5001, role="SENDER",
    )
    dash._frames_original = 40
    dash._data_bytes = 40 * 46
    dash.start()

    try:
        for idx in range(40):
            dash.frame_sent(idx)
            dash.update_window(max(0, idx - 3), idx + 1)
            dash.log(f"Sent frame idx={idx} seq={idx % 256}", style="cyan")
            time.sleep(0.08)

            rtt = random.gauss(30, 8)
            dash.update_rtt(max(rtt, 5), 30.0, 150.0)

            if random.random() < 0.15:
                dash.frame_timeout(idx)
                dash.log(f"TIMEOUT idx={idx}", style="bold yellow")
                time.sleep(0.05)
                dash.frame_retransmit(idx)
                dash.log(f"Retransmit idx={idx}", style="yellow")

            dash.frame_acked(idx)
            dash.log(f"ACK idx={idx}", style="green")
    finally:
        dash.stop()

    print("\nSelf-test done.")
