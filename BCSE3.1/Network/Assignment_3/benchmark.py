"""
benchmark.py
============
Automated benchmark sweep runner for CSMA protocols.

Runs simulations across parameter sweeps and collects metrics into a CSV
file for subsequent plotting by plot_results.py.

Sweeps
------
1. p-Persistent sweep : p ∈ {0.01, 0.05, 0.1, ..., 1.0} at fixed N
2. N sweep (all protocols): N ∈ {2, 3, 4, 5, 6, 8, 10, 15, 20}

Usage:
    python3 benchmark.py
    python3 benchmark.py --output results.csv --runs 5
    python3 benchmark.py --sim-time 2000 --frames 200

Generates:  results.csv  (consumed by plot_results.py)
"""

import argparse
import csv
import os
import sys
import time

from simulation import run_simulation, SimConfig, SimulationResult, PROTOCOL_NAMES
from csma_protocols import PROTOCOLS


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_CSV         = "results.csv"
DEFAULT_RUNS        = 5
DEFAULT_SIM_TIME    = 1000
DEFAULT_FRAMES      = 100
DEFAULT_SLOT_TIME   = 1.0
DEFAULT_FRAME_DUR   = 10.0
DEFAULT_PROP_DELAY  = 2.0

# p-Persistent sweep values
P_SWEEP = [0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
P_SWEEP_N = 5  # fixed N for p-sweep

# N sweep values (all protocols)
N_SWEEP = [2, 3, 4, 5, 6, 8, 10, 15, 20]
BEST_P  = 0.3  # p for p-persistent in N sweep (approximate 1/N-balanced)


# ---------------------------------------------------------------------------
# CSV field names
# ---------------------------------------------------------------------------

CSV_FIELDS = [
    "sweep_type", "protocol", "N", "p", "run",
    "collisions", "frames_sent", "attempts", "dropped",
    "avg_delay", "throughput", "utilization", "collision_rate",
]


# ---------------------------------------------------------------------------
# Progress display
# ---------------------------------------------------------------------------

def _progress_bar(current: int, total: int, start_time: float, width: int = 40) -> str:
    frac = current / max(total, 1)
    filled = int(frac * width)
    bar = "█" * filled + "░" * (width - filled)
    elapsed = time.time() - start_time
    if frac > 0:
        eta = elapsed / frac - elapsed
    else:
        eta = 0
    return f"[{bar}] {frac:>6.1%}  ETA: {eta:>5.1f}s"


# ---------------------------------------------------------------------------
# Sweep runners
# ---------------------------------------------------------------------------

def run_p_sweep(writer, config_base: dict, runs: int, start_time: float,
                progress_offset: int, total_runs: int) -> int:
    """Run p-persistent sweep across p values at fixed N."""
    count = progress_offset
    for p in P_SWEEP:
        for run in range(runs):
            config = SimConfig(
                num_stations=P_SWEEP_N,
                simulation_slots=config_base["sim_time"],
                slot_time=config_base["slot_time"],
                frame_duration=config_base["frame_duration"],
                propagation_delay=config_base["prop_delay"],
                frames_per_station=config_base["frames"],
                p_value=p,
            )
            result = run_simulation("p_persistent", config)
            row = result.summary_row()
            row["sweep_type"] = "p_sweep"
            row["run"] = run
            writer.writerow(row)
            count += 1
            print(f"\r  p-sweep: {_progress_bar(count, total_runs, start_time)}",
                  end="", flush=True)
    return count


def run_n_sweep(writer, config_base: dict, runs: int, start_time: float,
                progress_offset: int, total_runs: int) -> int:
    """Run all protocols across N values."""
    count = progress_offset
    protocols = list(PROTOCOLS.keys())

    for N in N_SWEEP:
        for proto in protocols:
            p = 1.0 / N if proto == "p_persistent" else BEST_P
            for run in range(runs):
                config = SimConfig(
                    num_stations=N,
                    simulation_slots=config_base["sim_time"],
                    slot_time=config_base["slot_time"],
                    frame_duration=config_base["frame_duration"],
                    propagation_delay=config_base["prop_delay"],
                    frames_per_station=config_base["frames"],
                    p_value=p,
                )
                result = run_simulation(proto, config)
                row = result.summary_row()
                row["sweep_type"] = "n_sweep"
                row["run"] = run
                writer.writerow(row)
                count += 1
                print(f"\r  N-sweep: {_progress_bar(count, total_runs, start_time)}",
                      end="", flush=True)
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="CSMA Benchmark Sweep Runner — Assignment 3",
    )
    parser.add_argument("--output", "-o", type=str, default=DEFAULT_CSV,
                        help=f"Output CSV file (default: {DEFAULT_CSV})")
    parser.add_argument("--runs", "-r", type=int, default=DEFAULT_RUNS,
                        help=f"Number of averaging runs per config (default: {DEFAULT_RUNS})")
    parser.add_argument("--sim-time", type=int, default=DEFAULT_SIM_TIME,
                        help=f"Simulation slots (default: {DEFAULT_SIM_TIME})")
    parser.add_argument("--frames", type=int, default=DEFAULT_FRAMES,
                        help=f"Frames per station (default: {DEFAULT_FRAMES})")
    parser.add_argument("--slot-time", type=float, default=DEFAULT_SLOT_TIME)
    parser.add_argument("--frame-duration", type=float, default=DEFAULT_FRAME_DUR)
    parser.add_argument("--prop-delay", type=float, default=DEFAULT_PROP_DELAY)

    args = parser.parse_args()

    config_base = {
        "sim_time":       args.sim_time,
        "frames":         args.frames,
        "slot_time":      args.slot_time,
        "frame_duration": args.frame_duration,
        "prop_delay":     args.prop_delay,
    }

    # Calculate total runs
    p_sweep_runs = len(P_SWEEP) * args.runs
    n_sweep_runs = len(N_SWEEP) * len(PROTOCOLS) * args.runs
    total_runs = p_sweep_runs + n_sweep_runs

    print("╔════════════════════════════════════════════════════════════╗")
    print("║         CSMA Benchmark Sweep — Assignment 3              ║")
    print("╠════════════════════════════════════════════════════════════╣")
    print(f"║  Output CSV       : {args.output:<37}║")
    print(f"║  Runs per config  : {args.runs:<37}║")
    print(f"║  p-sweep configs  : {len(P_SWEEP):<37}║")
    print(f"║  N-sweep configs  : {len(N_SWEEP) * len(PROTOCOLS):<37}║")
    print(f"║  Total simulations: {total_runs:<37}║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    start_time = time.time()

    with open(args.output, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
        writer.writeheader()

        # Sweep 1: p-Persistent
        print("Phase 1/2 — p-Persistent sweep (p varies, N fixed)")
        count = run_p_sweep(writer, config_base, args.runs, start_time, 0, total_runs)
        print()  # newline after progress bar

        # Sweep 2: All protocols, N varies
        print("Phase 2/2 — All protocols sweep (N varies)")
        count = run_n_sweep(writer, config_base, args.runs, start_time, count, total_runs)
        print()  # newline after progress bar

    elapsed = time.time() - start_time
    print()
    print(f"✅ Benchmark complete in {elapsed:.1f}s")
    print(f"   Output: {os.path.abspath(args.output)}")
    print(f"   Total runs: {total_runs}")
    print()
    print(f"Next step: python3 plot_results.py --csv {args.output}")


if __name__ == "__main__":
    main()
