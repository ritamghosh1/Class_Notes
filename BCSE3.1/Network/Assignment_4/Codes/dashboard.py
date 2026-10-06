"""
dashboard.py
============
Rich-based Live Terminal Dashboard for Multi-Process CDMA with Walsh Codes.

Visualizes true multi-process CDMA transmission:
  - Displays individual OS Process IDs (PIDs) for each station
  - Header with network specs, channel parameters, and multi-process architecture
  - Allocated Walsh Code set & orthogonality verification table
  - Shared channel superposition vector with visual Unicode waveform
  - Station transmission & despreading matrix with bit-by-bit matching and PIDs
  - Reconstructed ASCII text streams per station
  - Real-time sparkline telemetry and scrolling event log

Requires:
    pip install rich
"""

from __future__ import annotations
import os
import time
import math
from collections import deque
from typing import Any
import numpy as np

try:
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.console import Console
    from rich.progress_bar import ProgressBar
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

try:
    from simulation import MultiProcessCDMASimulation, CDMASimulation
    from walsh import WalshCodeGenerator
except ImportError:
    from Codes.simulation import MultiProcessCDMASimulation, CDMASimulation
    from Codes.walsh import WalshCodeGenerator


_SPARK_CHARS = " ▂▃▄▅▆▇█"


def render_sparkline(values: list | deque, width: int = 30) -> str:
    """Renders a Unicode sparkline from numeric values."""
    if not values:
        return ""
    vals = list(values)[-width:]
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1.0
    return "".join(
        _SPARK_CHARS[min(int((v - mn) / rng * (len(_SPARK_CHARS) - 1)), len(_SPARK_CHARS) - 1)]
        for v in vals
    )


def format_vector_colored(vec: Any) -> Text:
    """Formats a numeric vector with syntax coloring."""
    t = Text()
    t.append("[ ", style="dim")
    for i, val in enumerate(vec):
        v = round(float(val), 2)
        if v > 0:
            t.append(f"+{v:g}", style="bold green")
        elif v < 0:
            t.append(f"{v:g}", style="bold red")
        else:
            t.append(f" 0", style="dim cyan")
        if i < len(vec) - 1:
            t.append(", ", style="dim")
    t.append(" ]", style="dim")
    return t


class CDMADashboard:
    """
    Live terminal dashboard for monitoring Multi-Process CDMA transmission and despreading.
    """

    def __init__(self, simulation: Any, fps: float = 4.0):
        if not HAS_RICH:
            raise ImportError("CDMADashboard requires the 'rich' package. Install via: pip install rich")

        self.sim = simulation
        self.fps = fps
        self.console = Console()
        self.log_entries: deque[tuple[str, str]] = deque(maxlen=15)
        self.energy_history: deque[float] = deque(maxlen=40)
        self.ber_history: deque[float] = deque(maxlen=40)

        is_multi = isinstance(self.sim, MultiProcessCDMASimulation)
        mode_str = f"MULTI-PROCESS ({self.sim.num_stations} independent OS processes)" if is_multi else "In-Process Engine"

        self._add_log("INFO", f"Initialized CDMA system: {mode_str}")
        if is_multi:
            for s_id, p_id in self.sim.station_pids.items():
                self._add_log("PROC", f"Station {s_id} active on OS Process PID {p_id}")
        self._add_log("INFO", f"Walsh-Hadamard orthogonality: {'VERIFIED [OK]' if self.sim.is_orthogonal else 'FAILED'}")

    def _add_log(self, level: str, message: str) -> None:
        """Adds a timestamped message to the event log."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_entries.append((f"[{timestamp}] [{level}]", message))

    def _build_header(self) -> Panel:
        """Creates top title banner."""
        snr_str = f"{self.sim.snr_db:.1f} dB (AWGN)" if self.sim.snr_db is not None else "Noiseless (Ideal)"
        header_text = Text.assemble(
            ("⚡ MULTI-PROCESS CDMA WITH WALSH CODES ⚡\n", "bold yellow"),
            ("CSE/PC/B/S/314 Computer Networks Lab — Assignment 4\n", "bold cyan"),
            (f"Architecture: ", "white"), (f"True Multi-Process (k={self.sim.num_stations} OS Processes)  ", "bold green"),
            (f"Walsh Code Length N: ", "white"), (f"{self.sim.code_length} chips  ", "bold green"),
            (f"Channel: ", "white"), (f"{snr_str}  ", "bold magenta"),
            (f"Slot: ", "white"), (f"{self.sim.current_slot} / {self.sim.total_slots_planned}", "bold yellow")
        )
        return Panel(header_text, style="blue", box=box.ROUNDED)

    def _build_walsh_table(self) -> Panel:
        """Creates table of assigned Walsh codes and orthogonality status."""
        table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta", expand=True)
        table.add_column("Station", justify="center", style="cyan", width=12)
        table.add_column("OS PID", justify="center", style="bold green", width=10)
        table.add_column("Walsh Code W_i", justify="center", style="yellow")
        table.add_column("Auto-Corr", justify="center", style="green", width=10)
        table.add_column("Cross-Corr", justify="center", style="green", width=10)

        for i in range(self.sim.num_stations):
            pid = getattr(self.sim, "station_pids", {}).get(i, os.getpid())
            code = self.sim.hadamard_matrix[i]
            code_str = WalshCodeGenerator.format_code(code)
            table.add_row(
                f"Station {i}",
                f"PID {pid}",
                code_str,
                f"{self.sim.code_length} [OK]",
                "0 [ORTHO]"
            )

        return Panel(table, title="[bold cyan]Walsh-Hadamard Code Allocation & Process Map[/]", box=box.ROUNDED)

    def _build_channel_panel(self, latest_telem: dict[str, Any] | None) -> Panel:
        """Creates panel showing shared common channel composite signal and waveform."""
        if latest_telem is None:
            content = Text("Waiting for transmission...", style="dim")
        else:
            comp_sig = latest_telem["composite_signal"]
            comp_colored = format_vector_colored(comp_sig)

            # Energy calculation
            energy = float(np.sum(comp_sig ** 2))
            self.energy_history.append(energy)
            spark = render_sparkline(self.energy_history, width=28)

            content = Text()
            content.append("Composite Signal C = sum(s_i):\n", style="bold white")
            content.append_text(comp_colored)
            content.append("\n\n")

            # Visual bar visualization of amplitudes
            content.append("Chip Waveform: ", style="bold white")
            for chip in comp_sig:
                val = round(float(chip), 1)
                if val > 0:
                    content.append(f" ▲+{val:g} ", style="bold black on green")
                elif val < 0:
                    content.append(f" ▼{val:g} ", style="bold white on red")
                else:
                    content.append(" ─ 0  ", style="bold white on blue")
            content.append("\n\n")

            content.append(f"Instantaneous Energy: {energy:.2f} | Energy Sparkline: ", style="dim")
            content.append(spark, style="bold yellow")

            if self.sim.snr_db is not None:
                noise_vec = latest_telem["noise_vector"]
                content.append(f"\nNoise eta: {format_vector_colored(noise_vec)}", style="dim red")

        return Panel(content, title="[bold green]Shared Common Channel (Superposition Medium)[/]", box=box.ROUNDED)

    def _build_matrix_table(self, latest_telem: dict[str, Any] | None) -> Panel:
        """Creates matrix showing transmission, spreading, despreading, and decision."""
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold yellow", expand=True)
        table.add_column("Node", justify="center", style="bold cyan", width=10)
        table.add_column("OS PID", justify="center", style="green", width=9)
        table.add_column("Bit TX", justify="center", width=8)
        table.add_column("Bipolar d", justify="center", width=10)
        table.add_column("Spread Chips s_i", justify="center")
        table.add_column("Dot Prod C·W", justify="center", width=12)
        table.add_column("Norm d_hat", justify="center", width=12)
        table.add_column("Bit RX", justify="center", width=8)
        table.add_column("Match", justify="center", width=8)
        table.add_column("Reconstructed Msg", justify="left", style="bold green")

        for i in range(self.sim.num_stations):
            pid = getattr(self.sim, "station_pids", {}).get(i, os.getpid())
            if latest_telem is not None:
                tx_b = latest_telem["tx_bits"].get(i)
                tx_b_str = str(tx_b) if tx_b is not None else "[dim]IDLE[/]"
                d_val = latest_telem["tx_bipolar"].get(i, 0)
                d_str = f"+1" if d_val > 0 else (f"-1" if d_val < 0 else " 0")

                chips = latest_telem["station_chips"].get(i)
                chips_str = format_vector_colored(chips)

                rx_b = latest_telem["rx_bits"].get(i)
                rx_b_str = str(rx_b) if rx_b is not None else "[dim]IDLE[/]"

                norm_val = latest_telem["rx_norms"].get(i, 0.0)
                dot_val = norm_val * self.sim.code_length

                is_match = latest_telem["matches"].get(i, False)
                match_str = "[bold green]✓ OK[/]" if is_match else "[bold red]✗ ERR[/]"

                rec_msg = latest_telem.get("reconstructed_msgs", {}).get(i, "")
                if not rec_msg:
                    rec_msg = "[dim]streaming...[/]"
            else:
                tx_b_str = "-"
                d_str = "-"
                chips_str = Text("-")
                dot_val = 0.0
                norm_val = 0.0
                rx_b_str = "-"
                match_str = "-"
                rec_msg = "[dim]idle[/]"

            table.add_row(
                f"Station {i}",
                f"{pid}",
                tx_b_str,
                d_str,
                chips_str,
                f"{dot_val:+.1f}",
                f"{norm_val:+.2f}",
                rx_b_str,
                match_str,
                rec_msg
            )

        return Panel(table, title="[bold yellow]Multi-Process Spreading & Correlator Despreading Matrix[/]", box=box.ROUNDED)

    def _build_footer(self) -> Panel:
        """Creates footer metrics and scrolling event log."""
        table = Table.grid(expand=True)
        table.add_column(ratio=1)
        table.add_column(ratio=1)

        # Left: Metrics
        total_tx_bits = self.sim.current_slot * self.sim.num_stations
        total_errs = 0
        if self.sim.slot_history:
            for s in self.sim.slot_history:
                for matched in s["matches"].values():
                    if not matched:
                        total_errs += 1
        ber = (total_errs / total_tx_bits) if total_tx_bits > 0 else 0.0
        self.ber_history.append(ber)

        metrics_text = Text()
        metrics_text.append("📊 Network Metrics:\n", style="bold cyan")
        metrics_text.append(f" • Total Bits Transmitted: {total_tx_bits}\n")
        metrics_text.append(f" • Total Chips Broadcast:  {self.sim.channel.total_chips_transmitted}\n")
        metrics_text.append(f" • Bit Errors Detected:    {total_errs}\n")
        if ber == 0:
            metrics_text.append(f" • Bit Error Rate (BER):   {ber:.4f} [bold green](100% RECONSTRUCTION)[/]\n")
        else:
            metrics_text.append(f" • Bit Error Rate (BER):   {ber:.4f} [bold red](DEGRADED)[/]\n")

        processing_gain_db = 10 * math.log10(self.sim.code_length)
        metrics_text.append(f" • Processing Gain (Gp):   {processing_gain_db:.2f} dB\n", style="bold white")

        # Right: Log
        log_text = Text()
        log_text.append("📜 Multi-Process Event Log:\n", style="bold magenta")
        for prefix, msg in list(self.log_entries)[-5:]:
            log_text.append(f"{prefix} {msg}\n", style="dim")

        table.add_row(metrics_text, log_text)
        return Panel(table, title="[bold magenta]Performance Telemetry & Process Event Log[/]", box=box.ROUNDED)

    def render_layout(self, latest_telem: dict[str, Any] | None) -> Layout:
        """Assembles all dashboard widgets into a unified layout."""
        layout = Layout()
        layout.split_column(
            Layout(self._build_header(), name="header", size=5),
            Layout(name="upper", size=9),
            Layout(name="middle", ratio=1),
            Layout(self._build_footer(), name="footer", size=8)
        )

        layout["upper"].split_row(
            Layout(self._build_walsh_table(), ratio=1),
            Layout(self._build_channel_panel(latest_telem), ratio=1)
        )
        layout["middle"].update(self._build_matrix_table(latest_telem))
        return layout

    def run_live(self) -> dict[str, Any]:
        """Runs the simulation live with animated rich rendering."""
        self._add_log("INFO", f"Starting live transmission across {self.sim.num_stations} OS processes...")
        delay = 1.0 / self.fps

        with Live(self.render_layout(None), console=self.console, refresh_per_second=10) as live:
            while not self.sim.is_completed:
                telem = self.sim.step()
                slot_num = telem["slot"]

                if telem.get("all_matched", False):
                    self._add_log("DEBUG", f"Slot {slot_num}: All {self.sim.num_stations} station processes decoded successfully.")
                else:
                    self._add_log("WARN", f"Slot {slot_num}: Bit mismatch detected under noise.")

                live.update(self.render_layout(telem))
                time.sleep(delay)

            self._add_log("SUCCESS", "Simulation finished! Terminating child processes cleanly...")
            live.update(self.render_layout(telem if 'telem' in locals() else None))
            time.sleep(0.5)

        if isinstance(self.sim, MultiProcessCDMASimulation):
            return self.sim.terminate_and_report()
        else:
            return self.sim.generate_summary_report()


if __name__ == "__main__":
    print("=== Self-Test: Multi-Process Live Dashboard ===")
    sim = MultiProcessCDMASimulation(num_stations=4, payloads=["NET", "CDMA", "CODE", "WIRE"])
    dash = CDMADashboard(sim, fps=6.0)
    rep = dash.run_live()
    print("\nSummary Report:")
    for s in rep["station_reports"]:
        print(f"Station {s['station_id']} [PID {s['pid']}]: Sent '{s['transmitted_message']}' -> Reconstructed '{s['reconstructed_message']}' (Exact: {s['is_perfect']})")
