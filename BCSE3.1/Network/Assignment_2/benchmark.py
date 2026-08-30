"""
benchmark.py
============
Automated benchmark runner for Assignment 2 ARQ protocols.

Runs all three protocols (SAW, GBN, SR) across a sweep of error/loss
probabilities and collects metrics into a CSV file for plotting.

Usage:
    python3 benchmark.py [--input FILE] [--output CSV] [--window N] [--runs N]

The script starts receiver and sender as subprocesses, parses their stdout
for summary metrics, and appends one row per run to the CSV.

Generates:  results.csv
"""

import argparse
import csv
import os
import re
import subprocess
import sys
import time
import threading
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_INPUT   = "bench_input.txt"
DEFAULT_CSV     = "results.csv"
DEFAULT_WINDOW  = 4
DEFAULT_RUNS    = 3          # average over this many repetitions
DEFAULT_TIMEOUT = 300        # ms — tight enough to trigger retransmits quickly
DEFAULT_DELAY   = 10         # ms max channel delay (small to keep runs fast)
DEFAULT_PORT    = 5010       # avoid conflicts with manual tests on 5001

PROTOCOLS = ["saw", "gbn", "sr"]

# Error sweep (p_error, p_loss)
ERROR_SWEEP = [
    (0.0, 0.0),
    (0.1, 0.0),
    (0.2, 0.0),
    (0.3, 0.0),
    (0.4, 0.0),
    (0.5, 0.0),
]

LOSS_SWEEP = [
    (0.0, 0.0),
    (0.0, 0.1),
    (0.0, 0.2),
    (0.0, 0.3),
    (0.0, 0.4),
    (0.0, 0.5),
]

WINDOW_SWEEP = [1, 2, 4, 6, 8]   # for GBN and SR (fixed p=0)

# ---------------------------------------------------------------------------
# Metric extraction from sender / receiver stdout
# ---------------------------------------------------------------------------

def _extract(text: str, pattern: str, cast=float, default=0.0):
    m = re.search(pattern, text)
    return cast(m.group(1)) if m else default

def parse_sender_output(stdout: str) -> dict:
    return {
        "elapsed_s":        _extract(stdout, r"Total time\s+:\s+([\d.]+)"),
        "frames_original":  _extract(stdout, r"Original frames\s+:\s+(\d+)", int, 0),
        "retransmissions":  _extract(stdout, r"Retransmissions\s+:\s+(\d+)", int, 0),
        "data_bytes":       _extract(stdout, r"Data bytes sent\s+:\s+(\d+)", int, 0),
        "throughput_bps":   _extract(stdout, r"Throughput\s+:\s+([\d.]+)"),
        "efficiency_pct":   _extract(stdout, r"Channel efficiency\s+:\s+([\d.]+)"),
        "avg_rtt_ms":       _extract(stdout, r"Average RTT\s+:\s+([\d.]+)"),
        "srtt_ms":          _extract(stdout, r"Smoothed RTT\s+:\s+([\d.]+)"),
        "rto_ms":           _extract(stdout, r"Current RTO\s+:\s+([\d.]+)"),
        "frames_dropped":   _extract(stdout, r"Frames dropped\s+:\s+(\d+)", int, 0),
        "frames_corrupted": _extract(stdout, r"Frames corrupted\s+:\s+(\d+)", int, 0),
    }

# ---------------------------------------------------------------------------
# Single run
# ---------------------------------------------------------------------------

def run_once(protocol: str, window: int, p_error: float, p_loss: float,
             input_file: str, port: int,
             timeout_ms: float, delay_ms: float) -> dict | None:
    """
    Spawn receiver + sender subprocesses, wait for completion, parse output.
    Returns a metrics dict or None on failure.
    """
    recv_cmd = [
        sys.executable, "receiver.py",
        "--protocol", protocol,
        "--window",   str(window),
        "--port",     str(port),
        "--output",   "/dev/null",
        "--payload",  "46",
    ]
    send_cmd = [
        sys.executable, "sender.py",
        "--protocol", protocol,
        "--window",   str(window),
        "--port",     str(port),
        "--input",    input_file,
        "--payload",  "46",
        "--p-error",  str(p_error),
        "--p-loss",   str(p_loss),
        "--delay",    str(delay_ms),
        "--timeout",  str(timeout_ms),
    ]

    recv_proc = subprocess.Popen(
        recv_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    time.sleep(0.4)   # give receiver time to bind

    try:
        send_result = subprocess.run(
            send_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
    except subprocess.TimeoutExpired:
        recv_proc.kill()
        print(f"    TIMEOUT — {protocol} p_e={p_error} p_l={p_loss} w={window}")
        return None
    finally:
        try:
            recv_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            recv_proc.kill()

    if send_result.returncode != 0:
        print(f"    ERROR — sender exited {send_result.returncode}")
        return None

    metrics = parse_sender_output(send_result.stdout)
    return metrics


# ---------------------------------------------------------------------------
# Averaged run
# ---------------------------------------------------------------------------

def run_averaged(protocol: str, window: int, p_error: float, p_loss: float,
                 input_file: str, port: int, runs: int,
                 timeout_ms: float, delay_ms: float) -> dict:
    """Run *runs* times and return averaged metrics."""
    all_metrics = []
    for r in range(runs):
        port_r = port + r   # different port per repetition to avoid reuse
        m = run_once(protocol, window, p_error, p_loss,
                     input_file, port_r, timeout_ms, delay_ms)
        if m:
            all_metrics.append(m)
        time.sleep(0.3)

    if not all_metrics:
        return {}

    averaged = {}
    for key in all_metrics[0]:
        vals = [m[key] for m in all_metrics if key in m]
        averaged[key] = sum(vals) / len(vals) if vals else 0.0

    return averaged


# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------

FIELDNAMES = [
    "protocol", "window", "p_error", "p_loss", "sweep_type",
    "elapsed_s", "frames_original", "retransmissions",
    "data_bytes", "throughput_bps", "efficiency_pct",
    "avg_rtt_ms", "srtt_ms", "rto_ms",
    "frames_dropped", "frames_corrupted",
]

def write_row(writer, row: dict) -> None:
    writer.writerow({k: row.get(k, "") for k in FIELDNAMES})


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automated ARQ benchmark — generates results.csv",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input",   default=DEFAULT_INPUT,  help="Input file to transmit")
    parser.add_argument("--output",  default=DEFAULT_CSV,    help="CSV output file")
    parser.add_argument("--window",  type=int, default=DEFAULT_WINDOW, help="Window size for GBN/SR")
    parser.add_argument("--runs",    type=int, default=DEFAULT_RUNS,   help="Repetitions per config")
    parser.add_argument("--port",    type=int, default=DEFAULT_PORT,   help="Base TCP port")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Initial RTO ms")
    parser.add_argument("--delay",   type=float, default=DEFAULT_DELAY,   help="Max delay ms")
    parser.add_argument("--quick",   action="store_true",
                        help="Run only a subset (error sweep, no window sweep)")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"[ERROR] Input file '{args.input}' not found. "
              f"Create it or pass --input <path>.")
        sys.exit(1)

    csv_path = args.output
    f_out = open(csv_path, "w", newline="")
    writer = csv.DictWriter(f_out, fieldnames=FIELDNAMES)
    writer.writeheader()
    f_out.flush()

    port = args.port
    total_runs = 0
    start_wall = time.time()

    def _run(sweep_type, protocol, window, p_error, p_loss):
        nonlocal port, total_runs
        label = f"{protocol.upper():3s} w={window} p_e={p_error:.1f} p_l={p_loss:.1f}"
        print(f"  [{label}] ... ", end="", flush=True)
        t0 = time.time()
        m = run_averaged(protocol, window, p_error, p_loss,
                         args.input, port, args.runs, args.timeout, args.delay)
        port += args.runs + 2
        elapsed = time.time() - t0
        if m:
            row = {"protocol": protocol, "window": window,
                   "p_error": p_error, "p_loss": p_loss,
                   "sweep_type": sweep_type, **m}
            write_row(writer, row)
            f_out.flush()
            print(f"eff={m.get('efficiency_pct',0):.1f}%  "
                  f"rtx={int(m.get('retransmissions',0))}  "
                  f"t={m.get('elapsed_s',0):.2f}s  [{elapsed:.1f}s wall]")
        else:
            print("FAILED")
        total_runs += 1

    # =====================================================================
    # Sweep 1: Error probability  (all three protocols, fixed window)
    # =====================================================================
    print("\n=== Sweep 1: Error probability (p_loss=0) ===")
    for p_error, p_loss in ERROR_SWEEP:
        for proto in PROTOCOLS:
            _run("error_sweep", proto, args.window, p_error, p_loss)

    # =====================================================================
    # Sweep 2: Loss probability  (all three protocols, fixed window)
    # =====================================================================
    print("\n=== Sweep 2: Loss probability (p_error=0) ===")
    for p_error, p_loss in LOSS_SWEEP:
        for proto in PROTOCOLS:
            _run("loss_sweep", proto, args.window, p_error, p_loss)

    # =====================================================================
    # Sweep 3: Window size (GBN and SR, no errors)
    # =====================================================================
    if not args.quick:
        print("\n=== Sweep 3: Window size (p=0) ===")
        for N in WINDOW_SWEEP:
            for proto in ["gbn", "sr"]:
                _run("window_sweep", proto, N, 0.0, 0.0)

    f_out.close()
    wall_total = time.time() - start_wall
    print(f"\nDone. {total_runs} configurations in {wall_total:.1f}s → '{csv_path}'")


if __name__ == "__main__":
    main()
