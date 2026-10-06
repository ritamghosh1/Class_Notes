# Benchmark Module Theory — `benchmark.py`

> **File**: `benchmark.py`  
> **Class**: `CDMABenchmark`  
> **Role**: Automated empirical evaluation of scalability and noise sensitivity  
> **Outputs**: `results.csv`, `benchmark_snr.csv`  

---

## 1. What This Module Does

`benchmark.py` executes automated performance sweeps across two primary dimensions:
1. **Station Count Scalability ($n = 2, 4, 8, 16, 32, 64$)**: Evaluates processing throughput, memory stability, and error-free multi-user capacity limits.
2. **Noise Sensitivity Sweep (SNR from $-10 \text{ dB}$ to $+16 \text{ dB}$)**: Runs Monte Carlo trials of 10,000+ bits per SNR step to evaluate empirical Bit Error Rate (BER) against theoretical antipodal signaling curves.

---

## 2. Theoretical Principles Evaluated

### 2.1 Multi-User Capacity Scaling
Under synchronous orthogonal CDMA, adding more stations does not increase inter-user interference:
$$\text{MUI} = 0, \quad \forall n \le N$$
The total information throughput of the channel scales linearly with $n$:
$$\text{Throughput}_{\text{total}} = n \cdot R_b = \frac{n}{T_b}$$
Because the chip duration is $T_c = T_b / N$, the aggregate channel chip rate remains constant:
$$R_c = \frac{N}{T_b}$$
When $n = N$, the spectral efficiency is fully maximized at $1 \text{ bit/s/Hz}$ for binary modulation.

### 2.2 Theoretical Bit Error Rate over AWGN
For BPSK / binary antipodal CDMA over an Additive White Gaussian Noise channel, the theoretical Bit Error Rate is governed by the Gaussian $Q$-function:
$$P_b = Q\left( \sqrt{\frac{2 E_b}{N_0}} \right) = Q\left( \sqrt{\text{SNR}_{\text{linear}}} \right)$$
where:
$$Q(x) = \frac{1}{\sqrt{2\pi}} \int_x^\infty e^{-u^2/2} du = \frac{1}{2} \text{erfc}\left( \frac{x}{\sqrt{2}} \right)$$

---

## 3. Data Export Specifications

### 3.1 `results.csv` Schema (Scalability Sweep)
| Column | Type | Description |
|---|---|---|
| `num_stations` | `int` | Number of simultaneous transmitting stations ($n$) |
| `code_length` | `int` | Allocated Walsh codeword dimension ($N$) |
| `bits_per_station` | `int` | Payload length per station |
| `total_bits` | `int` | Aggregate bits processed ($n \times \text{bits\_per\_station}$) |
| `total_chips` | `int` | Aggregate chips broadcast ($n \times \text{bits\_per\_station} \times N$) |
| `elapsed_seconds` | `float` | Wall-clock execution time |
| `bit_throughput_bps` | `float` | Processing rate in bits per second |
| `chip_throughput_cps` | `float` | Processing rate in chips per second |
| `total_errors` | `int` | Cumulative bit mismatches (expected: 0) |
| `ber` | `float` | Empirical Bit Error Rate (expected: 0.0000) |
| `all_perfect` | `bool` | True if 100% reconstruction was verified |

### 3.2 `benchmark_snr.csv` Schema (Noise Sweep)
| Column | Type | Description |
|---|---|---|
| `snr_db` | `float` | Channel Signal-to-Noise Ratio in dB |
| `num_stations` | `int` | Active transmitting stations |
| `code_length` | `int` | Walsh codeword dimension |
| `bits_evaluated` | `int` | Total bits evaluated across stations |
| `total_errors` | `int` | Number of bit errors detected |
| `empirical_ber` | `float` | Measured Bit Error Rate |
| `theoretical_ber` | `float` | Theoretical $Q(\sqrt{\text{SNR}})$ value |
