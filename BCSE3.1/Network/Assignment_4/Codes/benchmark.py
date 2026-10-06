"""
benchmark.py
============
Automated Benchmarking Suite for CDMA with Walsh Codes.

Evaluates performance, scalability, and error resilience:
  1. Station Scalability Sweep (n = 2, 4, 8, 16, 32, 64)
  2. AWGN Noise Sensitivity Sweep (SNR from -10 dB to +16 dB) -> Empirical BER vs Theoretical Q-function
  3. Payload Scaling Sweep (100 to 10,000 bits per station)
  4. Exports results to results.csv and benchmark_snr.csv

Usage:
    python3 Codes/benchmark.py
"""

from __future__ import annotations
import time
import math
import csv
import numpy as np
from typing import Any

try:
    from simulation import CDMASimulation
    from walsh import WalshCodeGenerator
except ImportError:
    from Codes.simulation import CDMASimulation
    from Codes.walsh import WalshCodeGenerator

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def q_function(x: float) -> float:
    """Computes Gaussian Q-function: Q(x) = 0.5 * erfc(x / sqrt(2))."""
    return 0.5 * math.erfc(x / math.sqrt(2.0))


class CDMABenchmark:
    """
    Executes comprehensive benchmark sweeps across station counts, SNR, and payloads.
    """

    def __init__(self, console: Console | None = None):
        self.console = console or (Console() if HAS_RICH else None)

    def benchmark_station_scalability(self,
                                      station_counts: list[int] = [2, 4, 8, 16, 32, 64],
                                      bits_per_station: int = 1000) -> list[dict[str, Any]]:
        """
        Benchmarks performance as station count scales from 2 to 64.
        """
        results = []
        if self.console:
            self.console.print(Panel(f"[bold cyan]Running Station Scalability Sweep ({bits_per_station} bits/station)[/]", box=box.ROUNDED))

        for n in station_counts:
            # Generate random bit payloads
            payloads = [np.random.randint(0, 2, size=bits_per_station).tolist() for _ in range(n)]

            start_t = time.perf_counter()
            sim = CDMASimulation(num_stations=n, snr_db=None, payloads=payloads)
            sim_report = sim.run_all()
            elapsed_t = time.perf_counter() - start_t

            total_bits = sim_report["total_bits"]
            total_chips = sim.channel.total_chips_transmitted
            bit_throughput = total_bits / elapsed_t if elapsed_t > 0 else 0.0
            chip_throughput = total_chips / elapsed_t if elapsed_t > 0 else 0.0

            row = {
                "num_stations": n,
                "code_length": sim.code_length,
                "bits_per_station": bits_per_station,
                "total_bits": total_bits,
                "total_chips": total_chips,
                "elapsed_seconds": elapsed_t,
                "bit_throughput_bps": bit_throughput,
                "chip_throughput_cps": chip_throughput,
                "total_errors": sim_report["total_errors"],
                "ber": sim_report["overall_ber"],
                "all_perfect": sim_report["all_perfect"]
            }
            results.append(row)

            if self.console:
                self.console.print(
                    f" • Stations: [bold green]{n:2d}[/] | Code Length N: [cyan]{sim.code_length:2d}[/] | "
                    f"Time: [yellow]{elapsed_t:6.3f}s[/] | Throughput: [white]{bit_throughput:8.0f} bit/s[/] | "
                    f"BER: [green]{sim_report['overall_ber']:.4f}[/] | Perfect: [bold green]{sim_report['all_perfect']}[/]"
                )

        return results

    def benchmark_snr_sweep(self,
                            num_stations: int = 4,
                            snr_range: list[float] = list(range(-10, 16, 2)),
                            bits_per_station: int = 5000) -> list[dict[str, Any]]:
        """
        Sweeps AWGN SNR to evaluate empirical BER vs theoretical Q-function.
        """
        results = []
        if self.console:
            self.console.print(Panel(f"[bold magenta]Running SNR Sensitivity Sweep ({num_stations} stations, {bits_per_station} bits/st)[/]", box=box.ROUNDED))

        for snr in snr_range:
            payloads = [np.random.randint(0, 2, size=bits_per_station).tolist() for _ in range(num_stations)]

            sim = CDMASimulation(num_stations=num_stations, snr_db=float(snr), payloads=payloads)
            sim_report = sim.run_all()

            # Theoretical BER for BPSK/DSSS over AWGN
            # Eb/N0_linear = 10^(SNR/10) * N (with processing gain)
            # In matched filter despreader with orthogonal codes, other users cancel perfectly.
            # Residual noise standard deviation on d_hat is sigma_noise / sqrt(N).
            # Effective SNR for decision is SNR_linear * N / total_active_power.
            snr_linear = 10.0 ** (snr / 10.0)
            # Signal amplitude is 1, noise std on normalized correlation is 1 / sqrt(snr_linear * N)
            effective_snr_amp = math.sqrt(snr_linear * sim.code_length)
            theoretical_ber = q_function(effective_snr_amp)

            row = {
                "snr_db": float(snr),
                "num_stations": num_stations,
                "code_length": sim.code_length,
                "bits_evaluated": sim_report["total_bits"],
                "total_errors": sim_report["total_errors"],
                "empirical_ber": sim_report["overall_ber"],
                "theoretical_ber": theoretical_ber
            }
            results.append(row)

            if self.console:
                self.console.print(
                    f" • SNR: [bold yellow]{snr:+3d} dB[/] | Total Bits: [cyan]{sim_report['total_bits']}[/] | "
                    f"Errors: [red]{sim_report['total_errors']:5d}[/] | "
                    f"Empirical BER: [magenta]{sim_report['overall_ber']:8.5f}[/] | "
                    f"Theoretical BER: [dim cyan]{theoretical_ber:8.5f}[/]"
                )

        return results

    def save_to_csv(self,
                    scalability_data: list[dict[str, Any]],
                    snr_data: list[dict[str, Any]],
                    results_csv_path: str = "results.csv",
                    snr_csv_path: str = "benchmark_snr.csv") -> None:
        """Saves benchmark datasets to CSV files."""
        # Save Scalability data
        if scalability_data:
            keys = list(scalability_data[0].keys())
            with open(results_csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(scalability_data)

        # Save SNR data
        if snr_data:
            keys = list(snr_data[0].keys())
            with open(snr_csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(snr_data)

    def print_scalability_table(self, data: list[dict[str, Any]]) -> None:
        """Renders rich summary table for scalability results."""
        if not HAS_RICH or not self.console:
            return

        table = Table(title="CDMA Scalability & Throughput Benchmark", box=box.HEAVY_EDGE, header_style="bold cyan")
        table.add_column("Stations (n)", justify="center", style="green")
        table.add_column("Code Len (N)", justify="center", style="yellow")
        table.add_column("Total Bits", justify="right")
        table.add_column("Total Chips", justify="right")
        table.add_column("Time (s)", justify="right", style="cyan")
        table.add_column("Bit Rate (bps)", justify="right", style="bold white")
        table.add_column("Chip Rate (cps)", justify="right", style="magenta")
        table.add_column("Errors", justify="center", style="green")
        table.add_column("BER", justify="center", style="bold green")

        for r in data:
            table.add_row(
                str(r["num_stations"]),
                str(r["code_length"]),
                f"{r['total_bits']:,}",
                f"{r['total_chips']:,}",
                f"{r['elapsed_seconds']:.3f}",
                f"{r['bit_throughput_bps']:,.0f}",
                f"{r['chip_throughput_cps']:,.0f}",
                str(r["total_errors"]),
                f"{r['ber']:.4f}"
            )

        self.console.print(table)


if __name__ == "__main__":
    print("=== Self-Test: CDMA Automated Benchmarks ===")
    bm = CDMABenchmark()
    scale_res = bm.benchmark_station_scalability(station_counts=[2, 4, 8, 16], bits_per_station=500)
    snr_res = bm.benchmark_snr_sweep(num_stations=4, snr_range=[-6, -3, 0, 3, 6, 9], bits_per_station=1000)
    bm.save_to_csv(scale_res, snr_res, results_csv_path="results.csv", snr_csv_path="benchmark_snr.csv")
    bm.print_scalability_table(scale_res)
    print("\nBenchmark CSVs exported successfully!")
