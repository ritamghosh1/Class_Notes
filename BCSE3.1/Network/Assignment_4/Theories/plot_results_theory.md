# Plotting Module Theory — `plot_results.py`

> **File**: `plot_results.py`  
> **Role**: Publication-grade scientific visualization generator  
> **Target Output**: `Plots/` directory (8 high-resolution figures)  
> **Backend**: Headless Matplotlib (`matplotlib.use('Agg')`)  

---

## 1. What This Module Does

`plot_results.py` translates the analytical equations and empirical simulation outputs into publication-quality figures. It covers matrix properties, time-domain waveforms, inner-product correlation responses, BER waterfall curves, and multi-user scalability.

---

## 2. Visualization Principles & Standards

All figures are generated adhering to IEEE Transactions formatting standards:
- **Resolution**: 300 DPI (`savefig.dpi = 300`) suitable for lab report insertion and formal print publications.
- **Color Palettes**: Accessible, high-contrast color choices (`tableau-10`, `bwr`, and `Blues`).
- **Typography**: Clean sans-serif font family with strict hierarchy:
  - Figure Supertitles: 14pt bold
  - Axis Titles: 12pt bold
  - Axis Labels: 11pt
  - Tick Labels & Legends: 9pt
- **Grid Structure**: Subtle dashed guidelines (`alpha=0.35, linestyle='--'`) for precise coordinate reading.

---

## 3. Overview of Generated Figures

| Figure File | Visualization Subject | Key Theoretical Principle Demonstrated |
|---|---|---|
| `fig1_walsh_orthogonal_matrix.png` | Hadamard Matrix $H_8$ & Gramian $G$ | Mutual orthogonality ($H \cdot H^T = 8 \cdot I_8$), zero off-diagonal cross-correlation |
| `fig2_cdma_encoding_superposition.png` | Multi-Station Waveforms & Composite $C(t)$ | Discrete-time chip spreading and linear channel superposition |
| `fig3_despreading_correlation.png` | Correlator Receiver Dot Products | Rejection of other users ($0$) and extraction of target station signal ($\pm N$) |
| `fig4_ber_vs_snr_awgn.png` | Semilogarithmic BER vs. SNR Curve | Empirical Monte Carlo validation against theoretical $Q(\sqrt{\text{SNR}})$ |
| `fig5_throughput_vs_stations.png` | Throughput vs. Station Count ($n=2 \dots 64$) | Linear multi-user capacity scaling under orthogonal spreading |
| `fig6_processing_gain_analysis.png` | Processing Gain ($G_p$) vs. Codeword Length | Logarithmic gain expansion: $G_p = 10 \log_{10}(N)$ dB |
| `fig7_multi_station_constellation.png` | Composite Amplitude Distribution | Central Limit Theorem convergence of multi-station channel voltages |
| `fig8_combined_summary.png` | 4-Panel Executive Lab Dashboard | Comprehensive lab summary combining matrix, waveform, correlator, and gain |
