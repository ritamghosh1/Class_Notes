"""
plot_results.py
===============
Generate all report graphs from results.csv produced by benchmark.py.

Produces the following figures (saved as PNG and shown interactively):

  Fig 1  — Efficiency vs Error Probability     (SAW / GBN / SR line chart)
  Fig 2  — Efficiency vs Loss Probability      (SAW / GBN / SR line chart)
  Fig 3  — Throughput vs Error Probability     (SAW / GBN / SR line chart)
  Fig 4  — Retransmissions vs Error Prob       (SAW / GBN / SR line chart)
  Fig 5  — Total Transfer Time vs Error Prob   (SAW / GBN / SR line chart)
  Fig 6  — Efficiency vs Window Size N         (GBN / SR line chart)
  Fig 7  — Throughput vs Window Size N         (GBN / SR line chart)
  Fig 8  — Baseline Comparison Bar Chart       (time / efficiency / throughput at p=0)
  Fig 9  — Theoretical vs Measured Efficiency  (SAW formula overlay)
  Fig 10 — Combined 2×2 Summary Panel         (for report insertion)

Usage:
    python3 plot_results.py [--csv results.csv] [--outdir plots/] [--no-show]

Requirements:
    pip install matplotlib pandas
    (or: pip3 install matplotlib pandas)
"""

import argparse
import os
import sys

try:
    import pandas as pd
    import matplotlib
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    import numpy as np
except ImportError:
    print("Required packages missing.  Install with:")
    print("    pip3 install matplotlib pandas numpy")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

COLORS = {
    "saw": "#E63946",   # vivid red
    "gbn": "#457B9D",   # steel blue
    "sr":  "#2A9D8F",   # teal
}
LABELS = {"saw": "Stop-and-Wait", "gbn": "Go-Back-N", "sr": "Selective Repeat"}
MARKERS = {"saw": "o", "gbn": "s", "sr": "^"}
LINE_KW = dict(linewidth=2.2, markersize=7)

matplotlib.rcParams.update({
    "figure.dpi":        150,
    "font.family":       "DejaVu Sans",
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.grid":         True,
    "grid.alpha":        0.35,
    "grid.linestyle":    "--",
    "legend.framealpha": 0.85,
})


def save(fig, name: str, outdir: str) -> None:
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, name)
    fig.savefig(path, bbox_inches="tight")
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Load and validate CSV
# ---------------------------------------------------------------------------

def load_csv(path: str) -> pd.DataFrame:
    if not os.path.isfile(path):
        print(f"[ERROR] CSV file '{path}' not found.")
        print("  Run:  python3 benchmark.py  first.")
        sys.exit(1)
    df = pd.read_csv(path)
    df["protocol"] = df["protocol"].str.lower().str.strip()
    print(f"Loaded {len(df)} rows from '{path}'")
    print(f"  Protocols : {sorted(df['protocol'].unique())}")
    print(f"  Sweeps    : {sorted(df['sweep_type'].unique())}")
    return df


# ---------------------------------------------------------------------------
# Figure helpers
# ---------------------------------------------------------------------------

def _proto_line(ax, df_sweep, x_col, y_col, ylabel, title,
                protos=("saw", "gbn", "sr")):
    for proto in protos:
        sub = df_sweep[df_sweep["protocol"] == proto].sort_values(x_col)
        if sub.empty:
            continue
        ax.plot(sub[x_col], sub[y_col],
                color=COLORS[proto],
                marker=MARKERS[proto],
                label=LABELS[proto],
                **LINE_KW)
    ax.set_xlabel(x_col.replace("_", " ").title(), fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.legend(fontsize=9)
    return ax


# ---------------------------------------------------------------------------
# Fig 1 — Efficiency vs Error Probability
# ---------------------------------------------------------------------------

def fig_efficiency_vs_error(df: pd.DataFrame, outdir: str, show: bool) -> None:
    sub = df[df["sweep_type"] == "error_sweep"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    _proto_line(ax, sub, "p_error", "efficiency_pct",
                "Channel Efficiency (%)",
                "Fig 1 — Channel Efficiency vs Bit-Error Probability")
    ax.set_xlim(-0.02, 0.52)
    ax.set_ylim(0, 105)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.annotate("Higher is better ↑", xy=(0.98, 0.95), xycoords="axes fraction",
                ha="right", fontsize=8, color="grey")
    fig.tight_layout()
    save(fig, "fig1_efficiency_vs_error.png", outdir)
    if show: plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# Fig 2 — Efficiency vs Loss Probability
# ---------------------------------------------------------------------------

def fig_efficiency_vs_loss(df: pd.DataFrame, outdir: str, show: bool) -> None:
    sub = df[df["sweep_type"] == "loss_sweep"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    _proto_line(ax, sub, "p_loss", "efficiency_pct",
                "Channel Efficiency (%)",
                "Fig 2 — Channel Efficiency vs Frame-Loss Probability")
    ax.set_xlim(-0.02, 0.52)
    ax.set_ylim(0, 105)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    fig.tight_layout()
    save(fig, "fig2_efficiency_vs_loss.png", outdir)
    if show: plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# Fig 3 — Throughput vs Error Probability
# ---------------------------------------------------------------------------

def fig_throughput_vs_error(df: pd.DataFrame, outdir: str, show: bool) -> None:
    sub = df[df["sweep_type"] == "error_sweep"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    _proto_line(ax, sub, "p_error", "throughput_bps",
                "Throughput (B/s)",
                "Fig 3 — Throughput vs Bit-Error Probability")
    ax.set_xlim(-0.02, 0.52)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    fig.tight_layout()
    save(fig, "fig3_throughput_vs_error.png", outdir)
    if show: plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# Fig 4 — Retransmissions vs Error Probability
# ---------------------------------------------------------------------------

def fig_retransmissions_vs_error(df: pd.DataFrame, outdir: str, show: bool) -> None:
    sub = df[df["sweep_type"] == "error_sweep"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    _proto_line(ax, sub, "p_error", "retransmissions",
                "Retransmissions (count)",
                "Fig 4 — Retransmissions vs Bit-Error Probability")
    ax.set_xlim(-0.02, 0.52)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.annotate("Lower is better ↓", xy=(0.98, 0.95), xycoords="axes fraction",
                ha="right", fontsize=8, color="grey")
    fig.tight_layout()
    save(fig, "fig4_retransmissions_vs_error.png", outdir)
    if show: plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# Fig 5 — Total Transfer Time vs Error Probability
# ---------------------------------------------------------------------------

def fig_time_vs_error(df: pd.DataFrame, outdir: str, show: bool) -> None:
    sub = df[df["sweep_type"] == "error_sweep"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    _proto_line(ax, sub, "p_error", "elapsed_s",
                "Total Transfer Time (s)",
                "Fig 5 — Transfer Time vs Bit-Error Probability")
    ax.set_xlim(-0.02, 0.52)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    fig.tight_layout()
    save(fig, "fig5_time_vs_error.png", outdir)
    if show: plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# Fig 6 — Efficiency vs Window Size N
# ---------------------------------------------------------------------------

def fig_efficiency_vs_window(df: pd.DataFrame, outdir: str, show: bool) -> None:
    sub = df[df["sweep_type"] == "window_sweep"]
    if sub.empty:
        print("  [Skip Fig 6] No window_sweep data (run without --quick).")
        return
    fig, ax = plt.subplots(figsize=(7, 4.5))
    _proto_line(ax, sub, "window", "efficiency_pct",
                "Channel Efficiency (%)",
                "Fig 6 — Efficiency vs Sender Window Size N  (p=0)",
                protos=("gbn", "sr"))
    ax.set_xlabel("Window Size N", fontsize=11)
    ax.set_ylim(0, 105)
    fig.tight_layout()
    save(fig, "fig6_efficiency_vs_window.png", outdir)
    if show: plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# Fig 7 — Throughput vs Window Size N
# ---------------------------------------------------------------------------

def fig_throughput_vs_window(df: pd.DataFrame, outdir: str, show: bool) -> None:
    sub = df[df["sweep_type"] == "window_sweep"]
    if sub.empty:
        print("  [Skip Fig 7] No window_sweep data (run without --quick).")
        return
    fig, ax = plt.subplots(figsize=(7, 4.5))
    _proto_line(ax, sub, "window", "throughput_bps",
                "Throughput (B/s)",
                "Fig 7 — Throughput vs Sender Window Size N  (p=0)",
                protos=("gbn", "sr"))
    ax.set_xlabel("Window Size N", fontsize=11)
    fig.tight_layout()
    save(fig, "fig7_throughput_vs_window.png", outdir)
    if show: plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# Fig 8 — Baseline Comparison Bar Chart (p=0)
# ---------------------------------------------------------------------------

def fig_baseline_bar(df: pd.DataFrame, outdir: str, show: bool) -> None:
    base = df[(df["sweep_type"] == "error_sweep") & (df["p_error"] == 0.0)]
    if base.empty:
        print("  [Skip Fig 8] No baseline (p=0) data.")
        return

    metrics = {
        "Total Time (s)":    "elapsed_s",
        "Throughput (B/s)":  "throughput_bps",
        "Efficiency (%)":    "efficiency_pct",
    }
    protos = ["saw", "gbn", "sr"]
    x = np.arange(len(metrics))
    width = 0.25

    fig, ax = plt.subplots(figsize=(8, 5))
    for i, proto in enumerate(protos):
        row = base[base["protocol"] == proto]
        if row.empty:
            continue
        vals = [row[col].values[0] for col in metrics.values()]
        rects = ax.bar(x + i * width, vals, width,
                       label=LABELS[proto],
                       color=COLORS[proto],
                       alpha=0.85,
                       edgecolor="white",
                       linewidth=0.8)
        ax.bar_label(rects, fmt="%.1f", padding=3, fontsize=8)

    ax.set_xticks(x + width)
    ax.set_xticklabels(list(metrics.keys()), fontsize=10)
    ax.set_title("Fig 8 — Baseline Protocol Comparison  (no errors, no loss)",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=9)
    fig.tight_layout()
    save(fig, "fig8_baseline_bar.png", outdir)
    if show: plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# Fig 9 — Theoretical vs Measured Efficiency (SAW)
# ---------------------------------------------------------------------------

def fig_theoretical_overlay(df: pd.DataFrame, outdir: str, show: bool) -> None:
    """
    Overlay the theoretical SAW efficiency formula on measured data.

    eta_SAW = (1 - p) / (1 + 2a)
    where a = T_prop / T_frame.

    We estimate 'a' from the measured avg_rtt_ms and frame transmission time.
    """
    sub = df[(df["sweep_type"] == "error_sweep") & (df["protocol"] == "saw")].sort_values("p_error")
    if sub.empty:
        print("  [Skip Fig 9] No SAW error_sweep data.")
        return

    # Estimate 'a' from baseline row
    base_row = sub[sub["p_error"] == 0.0]
    if base_row.empty:
        print("  [Skip Fig 9] No SAW baseline row.")
        return

    # T_frame = payload_size / link_speed (approx from throughput at p=0)
    # Use measured average RTT to back-calculate 2*T_prop
    rtt_ms   = float(base_row["avg_rtt_ms"].values[0])
    frames   = float(base_row["frames_original"].values[0])
    elapsed  = float(base_row["elapsed_s"].values[0])
    t_frame  = (elapsed / frames) * 1000   # ms per frame
    t_prop   = rtt_ms / 2.0               # one-way propagation estimate
    a        = t_prop / t_frame if t_frame > 0 else 0.5
    a        = max(a, 0.01)               # avoid division artefacts

    p_range  = np.linspace(0, 0.5, 200)
    eta_theory_saw = (1 - p_range) / (1 + 2 * a) * 100.0

    fig, ax = plt.subplots(figsize=(7, 4.5))
    # Measured
    ax.plot(sub["p_error"], sub["efficiency_pct"],
            color=COLORS["saw"], marker=MARKERS["saw"],
            label="SAW measured", **LINE_KW)
    # Theoretical
    ax.plot(p_range, eta_theory_saw,
            color=COLORS["saw"], linestyle="--", linewidth=1.8,
            label=f"SAW theory  η=(1-p)/(1+2a),  a≈{a:.2f}")

    ax.set_xlabel("Bit-Error Probability", fontsize=11)
    ax.set_ylabel("Efficiency (%)", fontsize=11)
    ax.set_title("Fig 9 — SAW: Theoretical vs Measured Efficiency", fontsize=12, fontweight="bold")
    ax.set_xlim(-0.02, 0.52)
    ax.set_ylim(0, 105)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.legend(fontsize=9)
    fig.tight_layout()
    save(fig, "fig9_theoretical_overlay.png", outdir)
    if show: plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# Fig 10 — Combined 2×2 Summary Panel (for report)
# ---------------------------------------------------------------------------

def fig_summary_panel(df: pd.DataFrame, outdir: str, show: bool) -> None:
    err_df = df[df["sweep_type"] == "error_sweep"]
    loss_df = df[df["sweep_type"] == "loss_sweep"]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle("ARQ Protocol Comparison — Summary", fontsize=14, fontweight="bold", y=1.01)

    # Top-left: efficiency vs error
    ax = axes[0, 0]
    _proto_line(ax, err_df, "p_error", "efficiency_pct",
                "Efficiency (%)", "Efficiency vs Error Probability")
    ax.set_ylim(0, 105)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))

    # Top-right: retransmissions vs error
    ax = axes[0, 1]
    _proto_line(ax, err_df, "p_error", "retransmissions",
                "Retransmissions", "Retransmissions vs Error Probability")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))

    # Bottom-left: efficiency vs loss
    ax = axes[1, 0]
    _proto_line(ax, loss_df, "p_loss", "efficiency_pct",
                "Efficiency (%)", "Efficiency vs Loss Probability")
    ax.set_ylim(0, 105)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))

    # Bottom-right: throughput vs error
    ax = axes[1, 1]
    _proto_line(ax, err_df, "p_error", "throughput_bps",
                "Throughput (B/s)", "Throughput vs Error Probability")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))

    for ax in axes.flat:
        ax.set_xlim(-0.02, 0.52)

    fig.tight_layout()
    save(fig, "fig10_summary_panel.png", outdir)
    if show: plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# RTT adaptation plot (reads timer history from a single run — optional)
# ---------------------------------------------------------------------------

def fig_rtt_adaptation_demo(outdir: str, show: bool) -> None:
    """
    Simulate RTT adaptation to show the EWMA convergence.
    (Does not require CSV — uses simulated data for demonstration.)
    """
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from timer import FrameTimer
    except ImportError:
        print("  [Skip RTT fig] Could not import timer.py")
        return
    import random

    random.seed(42)
    t = FrameTimer(initial_timeout_ms=500.0)
    srtt_hist, rto_hist, sample_hist = [], [], []

    # Phase 1: stable low RTT (~30 ms)
    for _ in range(20):
        s = random.gauss(30, 5)
        t.update_timeout(max(s, 1))
        srtt_hist.append(t.est_rtt_ms)
        rto_hist.append(t.timeout_ms)
        sample_hist.append(max(s, 1))

    # Phase 2: sudden spike (network congestion, ~150 ms)
    for _ in range(10):
        s = random.gauss(150, 20)
        t.update_timeout(max(s, 1))
        srtt_hist.append(t.est_rtt_ms)
        rto_hist.append(t.timeout_ms)
        sample_hist.append(max(s, 1))

    # Phase 3: recovery (~40 ms)
    for _ in range(20):
        s = random.gauss(40, 8)
        t.update_timeout(max(s, 1))
        srtt_hist.append(t.est_rtt_ms)
        rto_hist.append(t.timeout_ms)
        sample_hist.append(max(s, 1))

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(sample_hist))
    ax.scatter(x, sample_hist, color="#ADB5BD", s=18, zorder=2, label="Sample RTT")
    ax.plot(x, srtt_hist, color="#457B9D", linewidth=2.2, label="SRTT (smoothed)")
    ax.plot(x, rto_hist,  color="#E63946", linewidth=2.2, linestyle="--", label="RTO (timeout)")
    ax.axvline(20, color="grey", linewidth=1, linestyle=":")
    ax.axvline(30, color="grey", linewidth=1, linestyle=":")
    ax.text(10, max(rto_hist)*0.92, "Low RTT\n(stable)", ha="center", fontsize=8, color="grey")
    ax.text(25, max(rto_hist)*0.92, "Congestion\nspike",   ha="center", fontsize=8, color="grey")
    ax.text(40, max(rto_hist)*0.92, "Recovery",            ha="center", fontsize=8, color="grey")
    ax.set_xlabel("Frame Index", fontsize=11)
    ax.set_ylabel("Time (ms)", fontsize=11)
    ax.set_title("Fig 11 — Adaptive RTT / RTO Estimation (RFC 6298 EWMA)", fontsize=12, fontweight="bold")
    ax.legend(fontsize=9)
    fig.tight_layout()
    save(fig, "fig11_rtt_adaptation.png", outdir)
    if show: plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate report graphs from benchmark CSV",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--csv",     default="results.csv", help="Input CSV from benchmark.py")
    parser.add_argument("--outdir",  default="plots",       help="Output directory for PNGs")
    parser.add_argument("--no-show", action="store_true",   help="Don't open interactive windows")
    args = parser.parse_args()

    show = not args.no_show

    print(f"\nGenerating plots → '{args.outdir}/'")
    print("-" * 50)

    df = load_csv(args.csv)
    print()

    fig_efficiency_vs_error   (df, args.outdir, show)
    fig_efficiency_vs_loss    (df, args.outdir, show)
    fig_throughput_vs_error   (df, args.outdir, show)
    fig_retransmissions_vs_error(df, args.outdir, show)
    fig_time_vs_error         (df, args.outdir, show)
    fig_efficiency_vs_window  (df, args.outdir, show)
    fig_throughput_vs_window  (df, args.outdir, show)
    fig_baseline_bar          (df, args.outdir, show)
    fig_theoretical_overlay   (df, args.outdir, show)
    fig_summary_panel         (df, args.outdir, show)
    fig_rtt_adaptation_demo   (args.outdir, show)       # no CSV needed

    print("\nAll figures saved.")
    print(f"Open '{args.outdir}/' in Finder or embed PNGs in your report.")


if __name__ == "__main__":
    main()
