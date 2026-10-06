"""
plot_results.py
===============
Publication-Grade Visualization Generator for CDMA with Walsh Code Lab.

Generates 8 high-resolution figures in the Plots/ directory:
  - fig1_walsh_orthogonal_matrix.png: Walsh Matrix & Orthogonality Heatmap
  - fig2_cdma_encoding_superposition.png: Time-Domain Multi-Station Signal Waveforms
  - fig3_despreading_correlation.png: Correlator Receiver Despreading Bar Chart
  - fig4_ber_vs_snr_awgn.png: Empirical BER vs Theoretical Q-function in AWGN
  - fig5_throughput_vs_stations.png: System Multi-User Throughput Scaling
  - fig6_processing_gain_analysis.png: Processing Gain (Gp) vs Code Length
  - fig7_multi_station_constellation.png: Composite Signal Amplitude Distribution
  - fig8_combined_summary.png: Multi-Panel Combined Summary Dashboard

Usage:
    python3 Codes/plot_results.py
"""

from __future__ import annotations
import os
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Headless rendering
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

try:
    from walsh import WalshCodeGenerator
    from simulation import CDMASimulation
    from benchmark import CDMABenchmark, q_function
except ImportError:
    from Codes.walsh import WalshCodeGenerator
    from Codes.simulation import CDMASimulation
    from Codes.benchmark import CDMABenchmark, q_function


PLOTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Plots"))
os.makedirs(PLOTS_DIR, exist_ok=True)


# Matplotlib styling for publication quality
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.titlesize": 14,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "axes.grid": True,
    "grid.alpha": 0.35,
    "grid.linestyle": "--"
})


def plot_fig1_walsh_orthogonal_matrix():
    """Generates Walsh code matrix & Gramian orthogonality heatmaps."""
    n = 8
    H, _ = WalshCodeGenerator.get_walsh_set(n)
    is_ortho, G = WalshCodeGenerator.verify_orthogonality(H)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8))

    # Ax1: Hadamard Matrix H_8
    im1 = ax1.imshow(H, cmap="bwr", vmin=-1.5, vmax=1.5)
    ax1.set_title(f"Walsh-Hadamard Matrix $H_{{{n}}}$ ($N={n}$ chips)", fontweight="bold")
    ax1.set_xlabel("Chip Index $k$")
    ax1.set_ylabel("Station / Codeword Index $i$")
    ax1.set_xticks(range(n))
    ax1.set_yticks(range(n))
    for i in range(n):
        for j in range(n):
            val = H[i, j]
            text = f"+1" if val > 0 else f"-1"
            ax1.text(j, i, text, ha="center", va="center", color="white" if abs(val) > 0.5 else "black", fontsize=8, fontweight="bold")

    # Ax2: Gramian Orthogonality Matrix H * H^T
    im2 = ax2.imshow(G, cmap="Blues", vmin=0, vmax=n)
    ax2.set_title(f"Gramian Matrix $G = H_{{{n}}} \\cdot H_{{{n}}}^T = {n} \\cdot I_{{{n}}}$", fontweight="bold")
    ax2.set_xlabel("Codeword Index $j$")
    ax2.set_ylabel("Codeword Index $i$")
    ax2.set_xticks(range(n))
    ax2.set_yticks(range(n))
    for i in range(n):
        for j in range(n):
            val = G[i, j]
            ax2.text(j, i, f"{int(val)}", ha="center", va="center",
                     color="white" if val > n/2 else "black", fontsize=9, fontweight="bold")

    fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04, label="Chip Value")
    fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04, label="Inner Product")
    plt.tight_layout()

    out_path = os.path.join(PLOTS_DIR, "fig1_walsh_orthogonal_matrix.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")


def plot_fig2_cdma_encoding_superposition():
    """Plots multi-station time-domain chip waveforms and composite channel signal."""
    n = 4
    H, code_len = WalshCodeGenerator.get_walsh_set(n)
    # Define sample bit vector: Station 0=1, Station 1=0, Station 2=1, Station 3=0
    bits = [1, 0, 1, 0]
    bipolar = [1, -1, 1, -1]
    station_chips = [bipolar[i] * H[i] for i in range(n)]
    composite = sum(station_chips)

    fig, axes = plt.subplots(n + 1, 1, figsize=(10, 8), sharex=True)

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    t_chips = np.arange(code_len)

    for i in range(n):
        ax = axes[i]
        chips = station_chips[i]
        # Step plot for chip waveform
        ax.step(t_chips, chips, where="post", color=colors[i], linewidth=2.2, label=f"Station {i} (Bit={bits[i]}, d={bipolar[i]:+d})")
        ax.fill_between(t_chips, 0, chips, step="post", alpha=0.15, color=colors[i])
        ax.set_ylim(-1.6, 1.6)
        ax.set_yticks([-1, 0, 1])
        ax.set_ylabel(f"St {i} Amp")
        ax.legend(loc="upper right", framealpha=0.9)

    # Composite Channel Signal
    ax_comp = axes[n]
    ax_comp.step(t_chips, composite, where="post", color="#9467bd", linewidth=2.8, label=f"Composite Channel $C(t) = \\sum s_i(t)$")
    ax_comp.fill_between(t_chips, 0, composite, step="post", alpha=0.25, color="#9467bd")
    ax_comp.set_ylim(-n - 0.8, n + 0.8)
    ax_comp.set_yticks(range(-n, n + 1, 2))
    ax_comp.set_xlabel("Chip Interval $k$ within 1-Bit Duration")
    ax_comp.set_ylabel("Channel $C$")
    ax_comp.legend(loc="upper right", framealpha=0.9)

    plt.suptitle("CDMA Time-Domain Spreading & Channel Superposition ($N=4$)", fontweight="bold")
    plt.tight_layout()

    out_path = os.path.join(PLOTS_DIR, "fig2_cdma_encoding_superposition.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")


def plot_fig3_despreading_correlation():
    """Generates correlator receiver inner product bar chart showing zero MUI."""
    n = 4
    H, code_len = WalshCodeGenerator.get_walsh_set(n)
    bits = [1, 0, 1, 1]
    bipolar = [1, -1, 1, 1]
    station_chips = [bipolar[i] * H[i] for i in range(n)]
    composite = sum(station_chips)

    # Calculate inner products
    inner_prods = [np.dot(composite, H[i]) for i in range(n)]
    normalized = [val / code_len for val in inner_prods]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

    stations = [f"Station {i}\n($W_{{{i}}}$)" for i in range(n)]
    bar_colors = ["#2ca02c" if b == 1 else "#d62728" for b in bits]

    # Ax1: Unnormalized Dot Products
    bars1 = ax1.bar(stations, inner_prods, color=bar_colors, width=0.55, edgecolor="black", alpha=0.85)
    ax1.set_title("Correlator Receiver Dot Product: $Y_i = C \\cdot W_i$", fontweight="bold")
    ax1.set_ylabel("Dot Product Amplitude ($N \\cdot d_i$)")
    ax1.axhline(0, color="gray", linewidth=1.2)
    ax1.set_ylim(-code_len - 1.5, code_len + 1.5)
    for bar, val in zip(bars1, inner_prods):
        height = bar.get_height()
        va = "bottom" if height >= 0 else "top"
        ax1.annotate(f"{val:+d}", xy=(bar.get_x() + bar.get_width()/2, height),
                     xytext=(0, 4 if height >= 0 else -12), textcoords="offset points",
                     ha="center", va=va, fontweight="bold")

    # Ax2: Normalized Symbol Decision
    bars2 = ax2.bar(stations, normalized, color=bar_colors, width=0.55, edgecolor="black", alpha=0.85)
    ax2.set_title("Normalized Decision Metric: $\\hat{d}_i = Y_i / N$", fontweight="bold")
    ax2.set_ylabel("Decoded Bipolar Symbol $\\hat{d}_i$")
    ax2.axhline(0.5, color="green", linestyle=":", label="Decision Threshold (+0.5)")
    ax2.axhline(-0.5, color="red", linestyle=":", label="Decision Threshold (-0.5)")
    ax2.axhline(0, color="gray", linewidth=1)
    ax2.set_ylim(-1.5, 1.5)
    for bar, val, b in zip(bars2, normalized, bits):
        height = bar.get_height()
        va = "bottom" if height >= 0 else "top"
        ax2.annotate(f"{val:+.1f} \u2192 Bit {b}", xy=(bar.get_x() + bar.get_width()/2, height),
                     xytext=(0, 4 if height >= 0 else -12), textcoords="offset points",
                     ha="center", va=va, fontweight="bold")
    ax2.legend(loc="upper right", framealpha=0.9)

    plt.tight_layout()
    out_path = os.path.join(PLOTS_DIR, "fig3_despreading_correlation.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")


def plot_fig4_ber_vs_snr_awgn():
    """Plots Empirical BER vs Theoretical Q-function across SNR range."""
    snrs = np.arange(-10, 16, 2)
    empirical_ber = []
    theoretical_ber = []

    bm = CDMABenchmark()
    snr_data = bm.benchmark_snr_sweep(num_stations=4, snr_range=list(snrs), bits_per_station=2500)

    for row in snr_data:
        empirical_ber.append(max(row["empirical_ber"], 1e-5))
        theoretical_ber.append(max(row["theoretical_ber"], 1e-5))

    plt.figure(figsize=(8, 5.2))
    plt.semilogy(snrs, empirical_ber, "o-", color="#d62728", linewidth=2.2, markersize=7, label="Simulated CDMA (4 Stations, Monte Carlo)")
    plt.semilogy(snrs, theoretical_ber, "--", color="#1f77b4", linewidth=2.2, label="Theoretical BPSK/CDMA: $P_b = Q(\\sqrt{SNR})$")

    plt.title("Bit Error Rate (BER) vs. SNR in AWGN Channel", fontweight="bold")
    plt.xlabel("Channel Signal-to-Noise Ratio (SNR in dB)")
    plt.ylabel("Bit Error Rate (BER)")
    plt.ylim(1e-5, 1.0)
    plt.xlim(-11, 16)
    plt.legend(loc="upper right", framealpha=0.9)

    out_path = os.path.join(PLOTS_DIR, "fig4_ber_vs_snr_awgn.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")


def plot_fig5_throughput_vs_stations():
    """Plots Aggregate System Throughput scaling with station count."""
    stations = [2, 4, 8, 16, 32, 64]
    bm = CDMABenchmark()
    scale_data = bm.benchmark_station_scalability(station_counts=stations, bits_per_station=800)

    bit_rates = [r["bit_throughput_bps"] / 1000.0 for r in scale_data]  # kbps
    chip_rates = [r["chip_throughput_cps"] / 1000.0 for r in scale_data]

    fig, ax1 = plt.subplots(figsize=(8, 5))

    color = "#1f77b4"
    ax1.set_xlabel("Number of Transmitting Stations ($n$)")
    ax1.set_ylabel("Bit Throughput (kbit/s)", color=color, fontweight="bold")
    line1 = ax1.plot(stations, bit_rates, "s-", color=color, linewidth=2.2, markersize=7, label="Bit Throughput (kbps)")
    ax1.tick_params(axis="y", labelcolor=color)

    ax2 = ax1.twinx()
    color2 = "#2ca02c"
    ax2.set_ylabel("Chip Rate (kchip/s)", color=color2, fontweight="bold")
    line2 = ax2.plot(stations, chip_rates, "^--", color=color2, linewidth=2.2, markersize=7, label="Chip Rate (kcps)")
    ax2.tick_params(axis="y", labelcolor=color2)

    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper left", framealpha=0.9)

    plt.title("CDMA System Multi-User Scalability & Processing Speed", fontweight="bold")
    plt.tight_layout()

    out_path = os.path.join(PLOTS_DIR, "fig5_throughput_vs_stations.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")


def plot_fig6_processing_gain_analysis():
    """Plots Processing Gain (Gp) vs Walsh Code Length."""
    n_values = [2, 4, 8, 16, 32, 64, 128]
    gp_db = [10.0 * math.log10(n) for n in n_values]

    plt.figure(figsize=(8, 4.8))
    plt.plot(n_values, gp_db, "D-", color="#ff7f0e", linewidth=2.2, markersize=8)

    for x, y in zip(n_values, gp_db):
        plt.annotate(f"{y:.1f} dB", xy=(x, y), xytext=(-6, 9), textcoords="offset points", fontweight="bold")

    plt.xscale("log", base=2)
    plt.xticks(n_values, [str(n) for n in n_values])
    plt.title("CDMA Processing Gain: $G_p = 10 \\log_{10}(N)$ dB vs. Code Length", fontweight="bold")
    plt.xlabel("Walsh Codeword Dimension / Spreading Factor ($N$)")
    plt.ylabel("Processing Gain $G_p$ (dB)")

    out_path = os.path.join(PLOTS_DIR, "fig6_processing_gain_analysis.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")


def plot_fig7_multi_station_constellation():
    """Plots amplitude histogram of composite channel signal for 4 and 8 stations."""
    # Monte Carlo simulation of 5000 slots
    slots = 5000
    H4, _ = WalshCodeGenerator.get_walsh_set(4)
    H8, _ = WalshCodeGenerator.get_walsh_set(8)

    # 4 Stations
    bits4 = np.random.choice([-1, 1], size=(4, slots))
    comp4 = np.sum(bits4[:, :, None] * H4[:, None, :], axis=0).flatten()

    # 8 Stations
    bits8 = np.random.choice([-1, 1], size=(8, slots))
    comp8 = np.sum(bits8[:, :, None] * H8[:, None, :], axis=0).flatten()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)

    bins4 = np.arange(min(comp4) - 0.5, max(comp4) + 1.5, 1)
    ax1.hist(comp4, bins=bins4, density=True, color="#1f77b4", edgecolor="black", alpha=0.8)
    ax1.set_title("Composite Signal Amplitudes ($n=4$ Stations)", fontweight="bold")
    ax1.set_xlabel("Channel Amplitude $C[k]$")
    ax1.set_ylabel("Probability Density")

    bins8 = np.arange(min(comp8) - 0.5, max(comp8) + 1.5, 1)
    ax2.hist(comp8, bins=bins8, density=True, color="#2ca02c", edgecolor="black", alpha=0.8)
    ax2.set_title("Composite Signal Amplitudes ($n=8$ Stations)", fontweight="bold")
    ax2.set_xlabel("Channel Amplitude $C[k]$")

    plt.suptitle("CDMA Common Channel Multi-User Voltage Distribution (Binomial CLT)", fontweight="bold")
    plt.tight_layout()

    out_path = os.path.join(PLOTS_DIR, "fig7_multi_station_constellation.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")


def plot_fig8_combined_summary():
    """Generates an executive 4-panel dashboard summary figure."""
    fig = plt.figure(figsize=(13, 9))
    gs = gridspec.GridSpec(2, 2, figure=fig)

    # Subplot 1: Walsh Orthogonality Heatmap
    ax1 = fig.add_subplot(gs[0, 0])
    H, _ = WalshCodeGenerator.get_walsh_set(4)
    _, G = WalshCodeGenerator.verify_orthogonality(H)
    im1 = ax1.imshow(G, cmap="Blues", vmin=0, vmax=4)
    ax1.set_title("(a) Orthogonality Gramian ($H_4 \\cdot H_4^T = 4 I_4$)", fontweight="bold")
    ax1.set_xticks(range(4))
    ax1.set_yticks(range(4))
    for i in range(4):
        for j in range(4):
            ax1.text(j, i, f"{int(G[i,j])}", ha="center", va="center", fontweight="bold",
                     color="white" if G[i,j] > 2 else "black")

    # Subplot 2: Multi-Station Spreading & Superposition
    ax2 = fig.add_subplot(gs[0, 1])
    bits = [1, -1, 1, -1]
    chips = [bits[i] * H[i] for i in range(4)]
    comp = sum(chips)
    t = np.arange(4)
    ax2.step(t, comp, where="post", color="#9467bd", linewidth=2.5, label="Composite $C(t)$")
    ax2.fill_between(t, 0, comp, step="post", alpha=0.25, color="#9467bd")
    ax2.set_title("(b) Channel Superposition Waveform ($N=4$)", fontweight="bold")
    ax2.set_xlabel("Chip Interval $k$")
    ax2.set_ylabel("Channel Voltage")
    ax2.set_ylim(-5, 5)
    ax2.legend(loc="upper right")

    # Subplot 3: Correlator Despreading Peak
    ax3 = fig.add_subplot(gs[1, 0])
    dots = [np.dot(comp, H[i]) for i in range(4)]
    stations = [f"St {i}" for i in range(4)]
    colors = ["#2ca02c" if d > 0 else "#d62728" for d in dots]
    bars = ax3.bar(stations, dots, color=colors, width=0.5, edgecolor="black")
    ax3.set_title("(c) Despreading Correlation Peaks ($C \\cdot W_i$)", fontweight="bold")
    ax3.set_ylabel("Correlation Value")
    ax3.set_ylim(-5.5, 5.5)
    for b, d in zip(bars, dots):
        ax3.annotate(f"{d:+d}", xy=(b.get_x() + b.get_width()/2, d),
                     xytext=(0, 4 if d > 0 else -12), textcoords="offset points",
                     ha="center", fontweight="bold")

    # Subplot 4: Processing Gain Scaling
    ax4 = fig.add_subplot(gs[1, 1])
    n_vals = [2, 4, 8, 16, 32, 64]
    gp_vals = [10 * math.log10(x) for x in n_vals]
    ax4.plot(n_vals, gp_vals, "o-", color="#ff7f0e", linewidth=2.2)
    ax4.set_xscale("log", base=2)
    ax4.set_xticks(n_vals)
    ax4.set_xticklabels([str(x) for x in n_vals])
    ax4.set_title("(d) Processing Gain ($G_p = 10 \\log_{10} N$ dB)", fontweight="bold")
    ax4.set_xlabel("Number of Chips / Stations ($N$)")
    ax4.set_ylabel("Gain (dB)")

    plt.suptitle("CDMA with Walsh Codes — Comprehensive Technical Summary", fontsize=15, fontweight="bold")
    plt.tight_layout()

    out_path = os.path.join(PLOTS_DIR, "fig8_combined_summary.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")


def generate_all_plots():
    """Generates all 8 technical figures sequentially."""
    print("=== Generating All Publication-Grade Plots ===")
    plot_fig1_walsh_orthogonal_matrix()
    plot_fig2_cdma_encoding_superposition()
    plot_fig3_despreading_correlation()
    plot_fig4_ber_vs_snr_awgn()
    plot_fig5_throughput_vs_stations()
    plot_fig6_processing_gain_analysis()
    plot_fig7_multi_station_constellation()
    plot_fig8_combined_summary()
    print(f"\nAll plots successfully saved to: {PLOTS_DIR}\n")


if __name__ == "__main__":
    generate_all_plots()
