"""
plot_results.py
===============
Generate all report graphs from results.csv produced by benchmark.py.

Produces the following figures (saved as PNG and shown interactively):

  Fig 1  — p-Persistent: Collisions vs p          (fixed N)
  Fig 2  — p-Persistent: Avg Delay vs p            (fixed N)
  Fig 3  — p-Persistent: Throughput vs p            (fixed N)
  Fig 4  — All Protocols: Collisions vs N
  Fig 5  — All Protocols: Avg Delay vs N
  Fig 6  — All Protocols: Throughput vs N
  Fig 7  — Combined 2×3 Summary Panel              (for report)
  Fig 8  — Theoretical Throughput Curves            (overlay)
  Fig 9  — p-Persistent Throughput Heatmap (p × N)  (scope extra)

Usage:
    python3 plot_results.py
    python3 plot_results.py --csv results.csv --outdir plots/ --no-show

Requirements:
    pip install matplotlib pandas numpy
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
# Styling (consistent with Assignment 2)
# ---------------------------------------------------------------------------

COLORS = {
    "non_persistent": "#E63946",   # vivid red
    "1_persistent":   "#457B9D",   # steel blue
    "p_persistent":   "#2A9D8F",   # teal
    "csma_cd":        "#F4A261",   # amber
}

LABELS = {
    "non_persistent": "Non-Persistent",
    "1_persistent":   "1-Persistent",
    "p_persistent":   "p-Persistent",
    "csma_cd":        "CSMA/CD",
}

MARKERS = {
    "non_persistent": "o",
    "1_persistent":   "s",
    "p_persistent":   "^",
    "csma_cd":        "D",
}

LINE_KW = dict(linewidth=3.0, markersize=9)

matplotlib.rcParams.update({
    "figure.dpi":        300,
    "font.family":       "sans-serif",
    "font.size":         12,
    "axes.labelsize":    14,
    "axes.titlesize":    16,
    "xtick.labelsize":   12,
    "ytick.labelsize":   12,
    "legend.fontsize":   12,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.grid":         True,
    "grid.alpha":        0.5,
    "grid.linestyle":    "-",
    "legend.framealpha": 0.9,
    "legend.edgecolor":  "gray",
})


def save(fig, name: str, outdir: str) -> None:
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, name)
    fig.savefig(path, bbox_inches="tight")
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Load CSV
# ---------------------------------------------------------------------------

def load_csv(path: str) -> pd.DataFrame:
    if not os.path.isfile(path):
        print(f"[ERROR] CSV file '{path}' not found.")
        print(f"        Run benchmark.py first to generate it.")
        sys.exit(1)

    df = pd.read_csv(path)
    print(f"  Loaded {len(df)} rows from {path}")
    return df


# ---------------------------------------------------------------------------
# Figures 1–3: p-Persistent sweep (Collisions, Delay, Throughput vs p)
# ---------------------------------------------------------------------------

def plot_p_sweep(df: pd.DataFrame, outdir: str, show: bool):
    """Plot metrics vs p for p-persistent CSMA."""
    p_data = df[df["sweep_type"] == "p_sweep"].copy()
    if p_data.empty:
        print("  [WARN] No p-sweep data found, skipping Figs 1–3.")
        return

    # Average over runs
    avg = p_data.groupby("p").agg({
        "collisions": "mean",
        "avg_delay":  "mean",
        "throughput": "mean",
    }).reset_index()

    metrics = [
        ("collisions", "Number of Collisions",     "Fig 1 — p-Persistent: Collisions vs p",
         "fig1_p_collisions.png"),
        ("avg_delay",  "Avg Transmission Delay",    "Fig 2 — p-Persistent: Avg Delay vs p",
         "fig2_p_delay.png"),
        ("throughput", "Throughput",                 "Fig 3 — p-Persistent: Throughput vs p",
         "fig3_p_throughput.png"),
    ]

    for metric, ylabel, title, fname in metrics:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(avg["p"], avg[metric],
                marker="^", color=COLORS["p_persistent"],
                **LINE_KW, label="p-Persistent")
        ax.set_xlabel("Persistence Probability (p)")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend()
        save(fig, fname, outdir)
        if show:
            plt.show()
        plt.close(fig)


# ---------------------------------------------------------------------------
# Figures 4–6: All protocols vs N (Collisions, Delay, Throughput)
# ---------------------------------------------------------------------------

def plot_n_sweep(df: pd.DataFrame, outdir: str, show: bool):
    """Plot metrics vs N for all four protocols."""
    n_data = df[df["sweep_type"] == "n_sweep"].copy()
    if n_data.empty:
        print("  [WARN] No N-sweep data found, skipping Figs 4–6.")
        return

    protocols = list(LABELS.keys())

    metrics = [
        ("collisions", "Number of Collisions",     "Fig 4 — All Protocols: Collisions vs N",
         "fig4_n_collisions.png"),
        ("avg_delay",  "Avg Transmission Delay",    "Fig 5 — All Protocols: Avg Delay vs N",
         "fig5_n_delay.png"),
        ("throughput", "Throughput",                 "Fig 6 — All Protocols: Throughput vs N",
         "fig6_n_throughput.png"),
    ]

    for metric, ylabel, title, fname in metrics:
        fig, ax = plt.subplots(figsize=(9, 5.5))

        for proto in protocols:
            proto_data = n_data[n_data["protocol"] == proto]
            if proto_data.empty:
                continue
            avg = proto_data.groupby("N")[metric].mean().reset_index()
            ax.plot(avg["N"], avg[metric],
                    marker=MARKERS[proto], color=COLORS[proto],
                    **LINE_KW, label=LABELS[proto])

        ax.set_xlabel("Number of Stations (N)")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend()
        save(fig, fname, outdir)
        if show:
            plt.show()
        plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 7: Combined 2×3 summary panel
# ---------------------------------------------------------------------------

def plot_combined_summary(df: pd.DataFrame, outdir: str, show: bool):
    """Create a 2×3 combined panel for report insertion."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))

    p_data = df[df["sweep_type"] == "p_sweep"]
    n_data = df[df["sweep_type"] == "n_sweep"]

    # Top row: p-sweep (Collisions, Delay, Throughput)
    if not p_data.empty:
        avg = p_data.groupby("p").agg({
            "collisions": "mean", "avg_delay": "mean", "throughput": "mean"
        }).reset_index()

        p_metrics = [
            (0, "collisions", "Collisions"),
            (1, "avg_delay",  "Avg Delay"),
            (2, "throughput", "Throughput"),
        ]

        for col, metric, ylabel in p_metrics:
            axes[0, col].plot(avg["p"], avg[metric],
                              marker="^", color=COLORS["p_persistent"], **LINE_KW)
            axes[0, col].set_xlabel("p")
            axes[0, col].set_ylabel(ylabel)
            axes[0, col].set_title(f"p-Persistent: {ylabel} vs p")

    # Bottom row: N-sweep (Collisions, Delay, Throughput)
    if not n_data.empty:
        n_metrics = [
            (0, "collisions", "Collisions"),
            (1, "avg_delay",  "Avg Delay"),
            (2, "throughput", "Throughput"),
        ]

        for col, metric, ylabel in n_metrics:
            for proto in LABELS:
                proto_data = n_data[n_data["protocol"] == proto]
                if proto_data.empty:
                    continue
                avg = proto_data.groupby("N")[metric].mean().reset_index()
                axes[1, col].plot(avg["N"], avg[metric],
                                  marker=MARKERS[proto], color=COLORS[proto],
                                  **LINE_KW, label=LABELS[proto])
            axes[1, col].set_xlabel("N")
            axes[1, col].set_ylabel(ylabel)
            axes[1, col].set_title(f"All Protocols: {ylabel} vs N")
            axes[1, col].legend(fontsize=8)

    fig.suptitle("CSMA Protocol Comparison — Summary", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "fig7_combined_summary.png", outdir)
    if show:
        plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 8: Theoretical throughput curves
# ---------------------------------------------------------------------------

def plot_theoretical_throughput(outdir: str, show: bool):
    """Plot theoretical throughput curves (S vs G) for CSMA variants."""
    G = np.linspace(0.01, 10, 500)
    a = 0.01  # propagation delay ratio (small for comparison)

    # Non-Persistent CSMA
    S_non = (G * np.exp(-a * G)) / (G * (1 + 2 * a) + np.exp(-a * G))

    # 1-Persistent CSMA (approximate)
    S_one = (G * (1 + G + a * G * (1 + G + a * G / 2)) * np.exp(-G * (1 + a))) / \
            (G * (1 + 2 * a) - (1 - np.exp(-a * G)) + (1 + a * G) * np.exp(-G * (1 + a)))
    S_one = np.clip(S_one, 0, 1)

    # Slotted CSMA (p-persistent approximation)
    S_p = (a * G * np.exp(-a * G) * (1 + a - np.exp(-a * G))) / \
          ((1 + a) * (1 - np.exp(-a * G)) + a * np.exp(-a * G))
    S_p = np.clip(S_p, 0, 1)

    # CSMA/CD (approximation)
    S_cd = 1.0 / (1 + 6.44 * a)
    S_cd_array = np.full_like(G, S_cd)

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(G, S_non, color=COLORS["non_persistent"], **LINE_KW,
            label=f"Non-Persistent (max ≈ {S_non.max():.2f})")
    ax.plot(G, S_one, color=COLORS["1_persistent"], **LINE_KW,
            label=f"1-Persistent (max ≈ {np.nanmax(S_one[np.isfinite(S_one)]):.2f})")
    ax.axhline(y=S_cd, color=COLORS["csma_cd"], linestyle="--", linewidth=2,
               label=f"CSMA/CD limit (≈ {S_cd:.2f})")

    ax.set_xlabel("Offered Load (G)")
    ax.set_ylabel("Normalized Throughput (S)")
    ax.set_title("Fig 8 — Theoretical Throughput: S vs G (a = 0.01)")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 1.05)
    ax.legend()
    save(fig, "fig8_theoretical_throughput.png", outdir)
    if show:
        plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 9: p-Persistent throughput heatmap (scope extra)
# ---------------------------------------------------------------------------

def plot_p_heatmap(df: pd.DataFrame, outdir: str, show: bool):
    """Heatmap of throughput for p-persistent across (p, N) combos."""
    # Need both p_sweep and n_sweep data for p_persistent
    p_data = df[(df["protocol"] == "p_persistent")].copy()
    if p_data.empty or len(p_data["p"].unique()) < 2:
        print("  [WARN] Insufficient p-persistent data for heatmap, skipping Fig 9.")
        return

    # Pivot: rows=N, cols=p, values=throughput
    pivot = p_data.groupby(["N", "p"])["throughput"].mean().reset_index()
    heatmap_data = pivot.pivot(index="N", columns="p", values="throughput")

    if heatmap_data.empty:
        print("  [WARN] Not enough data for heatmap, skipping Fig 9.")
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(heatmap_data.values, cmap="YlOrRd", aspect="auto",
                   origin="lower")
    ax.set_xticks(range(len(heatmap_data.columns)))
    ax.set_xticklabels([f"{p:.2f}" for p in heatmap_data.columns], rotation=45)
    ax.set_yticks(range(len(heatmap_data.index)))
    ax.set_yticklabels(heatmap_data.index)
    ax.set_xlabel("Persistence Probability (p)")
    ax.set_ylabel("Number of Stations (N)")
    ax.set_title("Fig 9 — p-Persistent Throughput Heatmap (p × N)")
    plt.colorbar(im, ax=ax, label="Throughput")
    save(fig, "fig9_p_heatmap.png", outdir)
    if show:
        plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate CSMA comparison plots from benchmark CSV.",
    )
    parser.add_argument("--csv", type=str, default="results.csv",
                        help="Input CSV file (default: results.csv)")
    parser.add_argument("--outdir", type=str, default="plots",
                        help="Output directory for PNG files (default: plots/)")
    parser.add_argument("--no-show", action="store_true",
                        help="Don't display plots interactively")

    args = parser.parse_args()
    show = not args.no_show

    print("╔════════════════════════════════════════════════════════════╗")
    print("║         CSMA Plot Generator — Assignment 3               ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    df = load_csv(args.csv)

    print("\n  Generating figures...")
    print("  " + "─" * 50)

    plot_p_sweep(df, args.outdir, show)
    plot_n_sweep(df, args.outdir, show)
    plot_combined_summary(df, args.outdir, show)
    plot_theoretical_throughput(args.outdir, show)
    plot_p_heatmap(df, args.outdir, show)

    print("  " + "─" * 50)
    print(f"\n  ✅ All figures saved to {os.path.abspath(args.outdir)}/")
    print()


if __name__ == "__main__":
    main()
