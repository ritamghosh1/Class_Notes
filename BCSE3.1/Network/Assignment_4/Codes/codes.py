"""
codes.py
========
Master Application and Unified Entry Point for Assignment 4: CDMA with Walsh Code.

Course: CSE/PC/B/S/314 Computer Networks Lab
Assignment 4: Implement CDMA with Walsh code.

Architecture:
  - TRUE MULTI-PROCESS EXECUTION: Each of the k stations runs in its own independent
    OS process with unique process isolation, communicating via IPC Pipes or TCP Sockets.

Capabilities:
  1. Live Rich Dashboard with real-time waveform, station matrix, and OS PIDs
  2. Step-by-step mathematical walkthrough of CDMA encoding/superposition/decoding
  3. Multi-Process verification of k independent stations
  4. Benchmark execution (scalability sweeps and SNR sweeps)
  5. Matplotlib publication-grade plot generation (8 figures saved to Plots/)
  6. Complete automated test suite runner (20 tests)
  7. Standalone Socket Server/Client runners for independent terminal windows

Usage:
    python3 Codes/codes.py                       # Interactive Rich Menu
    python3 Codes/codes.py --dashboard           # Launch Multi-Process Rich Dashboard
    python3 Codes/codes.py --walkthrough         # Step-by-step mathematical walkthrough
    python3 Codes/codes.py --benchmark           # Run benchmarks and save CSVs
    python3 Codes/codes.py --plot                # Generate all 8 figures
    python3 Codes/codes.py --test                # Run test suite
"""

from __future__ import annotations
import sys
import os
import argparse
import numpy as np

# Ensure Codes directory is in python search path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from walsh import WalshCodeGenerator
    from channel import Channel
    from station import Station
    from simulation import MultiProcessCDMASimulation, CDMASimulation
    from dashboard import CDMADashboard
    from benchmark import CDMABenchmark
    from plot_results import generate_all_plots
    from test_cdma import run_tests
except ImportError:
    from Codes.walsh import WalshCodeGenerator
    from Codes.channel import Channel
    from Codes.station import Station
    from Codes.simulation import MultiProcessCDMASimulation, CDMASimulation
    from Codes.dashboard import CDMADashboard
    from Codes.benchmark import CDMABenchmark
    from Codes.plot_results import generate_all_plots
    from Codes.test_cdma import run_tests

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, IntPrompt
    from rich import box
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

console = Console() if HAS_RICH else None


def print_banner():
    if not console:
        print("==================================================")
        print("  CDMA WITH WALSH CODES — COMPUTER NETWORKS LAB   ")
        print("==================================================")
        return

    main_pid = os.getpid()
    banner_text = Text.assemble(
        ("╔════════════════════════════════════════════════════════════════════════════════════╗\n", "bold cyan"),
        ("║               CSE/PC/B/S/314 COMPUTER NETWORKS LAB — ASSIGNMENT 4                  ║\n", "bold yellow"),
        ("║                   MULTI-PROCESS CDMA WITH WALSH CODES                              ║\n", "bold white"),
        ("║       k Independent OS Processes Sharing One Common Superposition Medium           ║\n", "bold green"),
        (f"║                   Orchestrator Host Process PID: {main_pid:<34}║\n", "dim cyan"),
        ("╚════════════════════════════════════════════════════════════════════════════════════╝", "bold cyan"),
    )
    console.print(banner_text)


def run_live_dashboard(num_stations: int = 4, fps: float = 5.0, snr_db: float | None = None):
    """Launches the animated Multi-Process Rich live terminal dashboard."""
    if console:
        console.print(f"\n[bold green]Spawning {num_stations} Independent OS Station Processes for Live Dashboard...[/]")

    sample_msgs = ["NET4", "CDMA", "SYNC", "WALS", "NODE", "DATA", "WIRE", "RF08"]
    msgs = [sample_msgs[i % len(sample_msgs)] for i in range(num_stations)]

    sim = MultiProcessCDMASimulation(num_stations=num_stations, snr_db=snr_db, payloads=msgs)
    dash = CDMADashboard(sim, fps=fps)
    report = dash.run_live()

    if console:
        table = Table(title="Multi-Process Simulation Final Verification Report", box=box.ROUNDED, header_style="bold cyan")
        table.add_column("Station", justify="center", style="cyan")
        table.add_column("OS PID", justify="center", style="bold green")
        table.add_column("Walsh Codeword", justify="center", style="yellow")
        table.add_column("Sent Message", justify="center", style="white")
        table.add_column("Reconstructed Message", justify="center", style="bold green")
        table.add_column("Errors", justify="center")
        table.add_column("BER", justify="center")
        table.add_column("Status", justify="center", style="bold green")

        for s in report["station_reports"]:
            table.add_row(
                f"Station {s['station_id']}",
                f"{s['pid']}",
                s["walsh_code"],
                s["transmitted_message"],
                s["reconstructed_message"],
                str(s["bit_errors"]),
                f"{s['ber']:.4f}",
                "[bold green]PERFECT [100%][/]" if s["is_perfect"] else "[bold red]FAILED[/]"
            )
        console.print(table)


def run_mathematical_walkthrough():
    """Provides a detailed numerical step-by-step CDMA walkthrough."""
    if not console:
        return

    console.print(Panel("[bold yellow]Mathematical Step-by-Step CDMA Transmission Walkthrough[/]", box=box.ROUNDED))

    n = 4
    H, N = WalshCodeGenerator.get_walsh_set(n)
    console.print(f"[bold cyan]1. System Setup:[/]")
    console.print(f" • Number of Stations: {n} (Modeled as {n} concurrent OS processes)")
    console.print(f" • Walsh Codeword Length N: {N} chips")
    console.print(f" • Hadamard Matrix H_4:")
    for i in range(n):
        console.print(f"   Station {i} Codeword W_{i} = {WalshCodeGenerator.format_code(H[i])}")

    # Orthogonality Gramian check
    is_ortho, G = WalshCodeGenerator.verify_orthogonality(H)
    console.print(f"\n[bold cyan]2. Orthogonality Verification (Gramian Matrix G = H · H^T):[/]")
    g_table = Table(box=box.SIMPLE)
    for j in range(n):
        g_table.add_column(f"W_{j}", justify="center")
    for i in range(n):
        row_str = [f"[bold green]{G[i, j]}[/]" if i == j else f"[dim]{G[i, j]}[/]" for j in range(n)]
        g_table.add_row(*row_str)
    console.print(g_table)
    console.print(f" • Diagonal is N={N} (Energy), Off-diagonals are 0 (Zero Inter-Station Cross-Talk)!\n")

    # Sample Transmission
    bits = [1, 0, 1, 0]
    bipolar = [1 if b == 1 else -1 for b in bits]
    chips = [bipolar[i] * H[i] for i in range(n)]
    composite = sum(chips)

    console.print(f"[bold cyan]3. Station Encoding & Spreading Phase (Per Process):[/]")
    tx_table = Table(box=box.ROUNDED)
    table_cols = ["Process", "Binary Bit b_i", "Bipolar Symbol d_i", "Walsh Code W_i", "Spread Chips s_i = d_i * W_i"]
    for c in table_cols:
        tx_table.add_column(c, justify="center")
    for i in range(n):
        tx_table.add_row(
            f"Station Process {i}",
            str(bits[i]),
            f"{bipolar[i]:+d}",
            WalshCodeGenerator.format_code(H[i]),
            WalshCodeGenerator.format_code(chips[i])
        )
    console.print(tx_table)

    console.print(f"\n[bold cyan]4. Common Channel Superposition Phase (Channel IPC Hub):[/]")
    console.print(f" • Linear Sum: C = s_0 + s_1 + s_2 + s_3")
    console.print(f" • Superimposed Channel Signal Vector: [bold magenta]{composite.tolist()}[/]\n")

    console.print(f"[bold cyan]5. Receiver Despreading & Reconstructive Correlator Phase (Per Process):[/]")
    rx_table = Table(box=box.ROUNDED)
    rx_cols = ["Receiver Process", "Target Walsh Code W_i", "Inner Product C · W_i", "Normalized d_hat = (C · W_i) / N", "Threshold Decision", "Match Status"]
    for c in rx_cols:
        rx_table.add_column(c, justify="center")

    for i in range(n):
        dot_prod = int(np.dot(composite, H[i]))
        norm = dot_prod / N
        rec_bit = 1 if norm > 0.5 else 0
        match_str = "[bold green]100% MATCH [OK][/]" if rec_bit == bits[i] else "[bold red]MISMATCH[/]"
        rx_table.add_row(
            f"Station Process {i}",
            WalshCodeGenerator.format_code(H[i]),
            f"{dot_prod:+d}",
            f"{norm:+.1f}",
            f"Bit {rec_bit}",
            match_str
        )
    console.print(rx_table)
    console.print("[bold green]✔ Perfect algebraic reconstruction demonstrated across all n concurrent station processes![/]\n")


def run_benchmark_cli():
    """Runs automated benchmarks."""
    if console:
        console.print(Panel("[bold cyan]Running CDMA Automated Benchmarks[/]", box=box.ROUNDED))
    bm = CDMABenchmark(console)
    scale_res = bm.benchmark_station_scalability([2, 4, 8, 16, 32, 64], bits_per_station=1000)
    snr_res = bm.benchmark_snr_sweep(num_stations=4, snr_range=list(range(-10, 16, 2)), bits_per_station=3000)
    bm.save_to_csv(scale_res, snr_res, results_csv_path="results.csv", snr_csv_path="benchmark_snr.csv")
    bm.print_scalability_table(scale_res)
    if console:
        console.print("[bold green]✔ Benchmarks complete. Datasets written to results.csv and benchmark_snr.csv[/]\n")


def run_plot_cli():
    """Generates all matplotlib plots."""
    if console:
        console.print(Panel("[bold magenta]Generating Publication-Grade Plots into Plots/[/]", box=box.ROUNDED))
    generate_all_plots()
    if console:
        console.print("[bold green]✔ All 8 PNG plots generated in Plots/ directory![/]\n")


def run_test_cli():
    """Runs automated test suite."""
    if console:
        console.print(Panel("[bold yellow]Running CDMA Automated Unit & Integration Tests (20 Tests)[/]", box=box.ROUNDED))
    run_tests()


def interactive_menu():
    """Displays interactive CLI menu."""
    while True:
        print_banner()
        menu_table = Table(box=box.ROUNDED, show_header=False, expand=True)
        menu_table.add_column("Option", style="bold yellow", width=10)
        menu_table.add_column("Action", style="white")

        menu_table.add_row("1", "🚀 Launch Multi-Process Live Rich Dashboard (4 Independent OS Processes)")
        menu_table.add_row("2", "🎛️  Custom Multi-Process Live Dashboard (Select k Processes & Noise)")
        menu_table.add_row("3", "📐 Step-by-Step Mathematical Walkthrough (Equations & Inner Products)")
        menu_table.add_row("4", "📊 Run Automated Scalability & SNR Benchmarks (Export CSVs)")
        menu_table.add_row("5", "📈 Generate All 8 Matplotlib Plots into Plots/")
        menu_table.add_row("6", "🧪 Run Full Automated Unit & Multi-Process Test Suite (20 Tests)")
        menu_table.add_row("0", "❌ Exit")

        console.print(menu_table)
        choice = Prompt.ask("[bold cyan]Select an option[/]", choices=["0", "1", "2", "3", "4", "5", "6"], default="1")

        if choice == "1":
            run_live_dashboard(num_stations=4, fps=5.0)
            Prompt.ask("\n[dim]Press Enter to return to menu...[/]")
        elif choice == "2":
            st_count = IntPrompt.ask("[bold cyan]Enter number of stations/processes (e.g. 2, 4, 8, 16)[/]", default=4)
            snr_input = Prompt.ask("[bold cyan]Enter SNR in dB for AWGN channel (or 'none' for ideal noiseless)[/]", default="none")
            snr_val = float(snr_input) if snr_input.lower() != "none" else None
            run_live_dashboard(num_stations=st_count, fps=5.0, snr_db=snr_val)
            Prompt.ask("\n[dim]Press Enter to return to menu...[/]")
        elif choice == "3":
            run_mathematical_walkthrough()
            Prompt.ask("\n[dim]Press Enter to return to menu...[/]")
        elif choice == "4":
            run_benchmark_cli()
            Prompt.ask("\n[dim]Press Enter to return to menu...[/]")
        elif choice == "5":
            run_plot_cli()
            Prompt.ask("\n[dim]Press Enter to return to menu...[/]")
        elif choice == "6":
            run_test_cli()
            Prompt.ask("\n[dim]Press Enter to return to menu...[/]")
        elif choice == "0":
            console.print("[bold yellow]Exiting CDMA System. Goodbye![/]")
            break


def main():
    parser = argparse.ArgumentParser(description="Multi-Process CDMA with Walsh Codes Simulation & Verification")
    parser.add_argument("--dashboard", action="store_true", help="Launch live animated Rich dashboard")
    parser.add_argument("--walkthrough", action="store_true", help="Run mathematical walkthrough")
    parser.add_argument("--stations", type=int, default=4, help="Number of transmitting stations (spawns k processes)")
    parser.add_argument("--snr", type=float, default=None, help="Channel SNR in dB (AWGN noise)")
    parser.add_argument("--fps", type=float, default=5.0, help="Dashboard frames per second")
    parser.add_argument("--benchmark", action="store_true", help="Run automated benchmarks and export CSV")
    parser.add_argument("--plot", action="store_true", help="Generate all 8 figures into Plots/")
    parser.add_argument("--test", action="store_true", help="Run automated test suite")

    args = parser.parse_args()

    if args.dashboard:
        run_live_dashboard(num_stations=args.stations, fps=args.fps, snr_db=args.snr)
    elif args.walkthrough:
        run_mathematical_walkthrough()
    elif args.benchmark:
        run_benchmark_cli()
    elif args.plot:
        run_plot_cli()
    elif args.test:
        run_test_cli()
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
