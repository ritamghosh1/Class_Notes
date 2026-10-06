# Technical Plot Analysis & Interpretation Guide

> **Directory**: `Plots/`  
> **Course**: CSE/PC/B/S/314 Computer Networks Lab — Assignment 4  
> **Subject**: Detailed physical and mathematical interpretation of all generated figures  

---

## Figure 1: Walsh-Hadamard Matrix & Orthogonality Gramian
**File**: `Plots/fig1_walsh_orthogonal_matrix.png`

![Figure 1](Plots/fig1_walsh_orthogonal_matrix.png)

### What the Plot Shows:
- **Left Subplot**: The $8 \times 8$ Hadamard Matrix $H_8$. Each cell represents a chip entry: $+1$ (blue) or $-1$ (red).
- **Right Subplot**: The Gramian matrix $G = H_8 \cdot H_8^T$, representing all pairwise inner products $\langle W_i, W_j \rangle$ between codewords.

### Physical & Mathematical Interpretation:
1. **Diagonal Dominance**: The diagonal elements are identically equal to $N = 8$. This reflects the zero-lag auto-correlation of each codeword, signifying that the signal energy accumulated over an 8-chip bit period is $8$.
2. **Zero Off-Diagonal Cross-Correlation**: Every off-diagonal entry ($i \neq j$) is strictly $0$. This visually confirms that no station leaks energy into any other station's correlator.
3. **Symmetry**: $H_8$ is symmetric ($H_8 = H_8^T$), meaning that rows and columns are interchangeable orthogonal bases.

---

## Figure 2: Time-Domain Multi-Station Spreading & Superposition
**File**: `Plots/fig2_cdma_encoding_superposition.png`

![Figure 2](Plots/fig2_cdma_encoding_superposition.png)

### What the Plot Shows:
- Subplots 1 to 4 show the time-domain chip step waveforms $s_i(t) = d_i \cdot W_i$ transmitted by 4 active stations within a single bit duration ($T_b = 4 \cdot T_c$).
- Subplot 5 shows the superimposed composite channel voltage waveform $C(t) = \sum_{i=0}^3 s_i(t)$.

### Physical & Mathematical Interpretation:
1. **Pulse Modulations**:
   - Station 0 ($b_0 = 1 \implies d_0 = +1$): Transmits $W_0 = [+1, +1, +1, +1]$.
   - Station 1 ($b_1 = 0 \implies d_1 = -1$): Transmits $-W_1 = [-1, +1, -1, +1]$.
   - Station 2 ($b_2 = 1 \implies d_2 = +1$): Transmits $W_2 = [+1, +1, -1, -1]$.
   - Station 3 ($b_3 = 0 \implies d_3 = -1$): Transmits $-W_3 = [-1, +1, +1, -1]$.
2. **Linear Addition**:
   - At chip interval $k=1$, all four waveforms have value $+1$. They constructively interfere to produce a peak voltage of $+4$.
   - At chip intervals $k=0, 2, 3$, two stations have $+1$ and two stations have $-1$, destructively interfering to produce an exact channel voltage of $0$.
   - The resulting composite channel vector is $C = [0, +4, 0, 0]$.

---

## Figure 3: Correlator Receiver Despreading & MUI Rejection
**File**: `Plots/fig3_despreading_correlation.png`

![Figure 3](Plots/fig3_despreading_correlation.png)

### What the Plot Shows:
- **Left Subplot**: Raw inner product values $Y_i = C \cdot W_i$ calculated at each receiver.
- **Right Subplot**: Normalized decision metric $\hat{d}_i = Y_i / N$ plotted against the decision thresholds ($\pm 0.5$).

### Physical & Mathematical Interpretation:
1. **Zero Multi-User Interference (MUI = 0)**:
   - For Station 0: $Y_0 = +4 \implies \hat{d}_0 = +1.0 \implies \text{Bit 1}$.
   - For Station 1: $Y_1 = -4 \implies \hat{d}_1 = -1.0 \implies \text{Bit 0}$.
   - For Station 2: $Y_2 = +4 \implies \hat{d}_2 = +1.0 \implies \text{Bit 1}$.
   - For Station 3: $Y_3 = -4 \implies \hat{d}_3 = -1.0 \implies \text{Bit 0}$.
2. **Threshold Margin**: The normalized metrics $\pm 1.0$ sit well outside the decision band $[-0.5, +0.5]$, providing a wide noise margin of $0.5$ units before an error can occur.

---

## Figure 4: Bit Error Rate (BER) vs. SNR in AWGN Channel
**File**: `Plots/fig4_ber_vs_snr_awgn.png`

![Figure 4](Plots/fig4_ber_vs_snr_awgn.png)

### What the Plot Shows:
- Semilogarithmic plot comparing empirical Monte Carlo BER (red points, 10,000 bits per step) against theoretical BPSK/CDMA BER (blue dashed curve, $P_b = Q(\sqrt{\text{SNR}})$) from $-10 \text{ dB}$ to $+14 \text{ dB}$.

### Physical & Mathematical Interpretation:
1. **The Waterfall Region**: As SNR increases past $0 \text{ dB}$, the Bit Error Rate drops sharply from $0.31$ down to below $0.005$ at $+14 \text{ dB}$, and reaches $0.0000$ (error-free) for SNR $\ge 18 \text{ dB}$.
2. **Agreement with Theory**: The simulated Monte Carlo points align with the theoretical $Q$-function curve, validating that the inner-product correlator functions as an optimal maximum-likelihood matched filter.

---

## Figure 5: Multi-User Throughput & Scalability
**File**: `Plots/fig5_throughput_vs_stations.png`

![Figure 5](Plots/fig5_throughput_vs_stations.png)

### What the Plot Shows:
- System bit throughput (kbit/s, blue line) and channel chip rate (kchip/s, green dashed line) as station count scales from $n = 2$ to $n = 64$.

### Physical & Mathematical Interpretation:
1. **Linear Capacity Scaling**: As $n$ increases, the aggregate bit throughput scales upward from $200 \text{ kbps}$ to over $400 \text{ kbps}$.
2. **Deterministic Processing**: Execution time scales as $O(n \cdot M \cdot N)$. Because matrix multiplications are executed via optimized vectorized BLAS operations, the simulation easily supports up to 64 concurrent stations without performance bottlenecks.

---

## Figure 6: Processing Gain ($G_p$) Analysis
**File**: `Plots/fig6_processing_gain_analysis.png`

![Figure 6](Plots/fig6_processing_gain_analysis.png)

### What the Plot Shows:
- Processing Gain $G_p = 10 \log_{10}(N)$ dB plotted against Walsh code dimension $N \in \{2, 4, 8, 16, 32, 64, 128\}$.

### Physical & Mathematical Interpretation:
1. **Logarithmic Scaling**: Doubling the code length adds exactly $+3.01 \text{ dB}$ of processing gain ($10 \log_{10}(2) \approx 3.01$).
2. **Jammer Margin**: At $N = 64$, the system achieves $18.06 \text{ dB}$ of processing gain, meaning an interfering jammer must transmit with over $64\times$ the power of the signal to corrupt communication.

---

## Figure 7: Composite Channel Amplitude Distribution (Central Limit Theorem)
**File**: `Plots/fig7_multi_station_constellation.png`

![Figure 7](Plots/fig7_multi_station_constellation.png)

### What the Plot Shows:
- Normalized probability density histograms of composite channel signal amplitudes $C[k]$ for $n = 4$ stations (left) and $n = 8$ stations (right).

### Physical & Mathematical Interpretation:
1. **Discrete Binomial Distribution**: Because each station contributes $\pm 1$, the sum of $n$ independent antipodal variables follows a symmetric binomial distribution over $\{-n, -n+2, \dots, n-2, n\}$.
2. **Convergence to Gaussian (CLT)**: As $n$ grows from 4 to 8 and beyond, the discrete voltage distribution approaches a continuous bell-shaped Gaussian envelope $\mathcal{N}(0, n)$, proving that the composite signal of many CDMA users resembles thermal Gaussian background noise.

---

## Figure 8: Comprehensive Technical Summary Dashboard
**File**: `Plots/fig8_combined_summary.png`

![Figure 8](Plots/fig8_combined_summary.png)

### What the Plot Shows:
- A 4-panel executive visualization combining:
  - Panel (a): Gramian Orthogonality Matrix ($H_4 \cdot H_4^T = 4 I_4$)
  - Panel (b): Channel Superposition Waveform ($C(t)$)
  - Panel (c): Despreading Correlation Peaks ($C \cdot W_i$)
  - Panel (d): Processing Gain Scaling Curve ($G_p = 10 \log_{10} N$ dB)

### Physical & Mathematical Interpretation:
This figure serves as the definitive visual summary of Assignment 4, providing a concise reference that connects algebraic code properties with physical signal waveforms and error-free multi-user reconstruction.
