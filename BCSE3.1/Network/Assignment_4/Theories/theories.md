# Computer Networks — Assignment 4
## Code Division Multiple Access (CDMA) with Walsh-Hadamard Codes
### Multi-Process Network Architecture & Hardware Emulation

> **Course**: CSE/PC/B/S/314 Computer Networks Lab  
> **Topic**: Channelization / Medium Access Control — Multi-Process CDMA with Orthogonal Walsh Codes  
> **Due Date**: 05–09 October 2026  
> **Architecture Constraint**: *$k$ stations sharing the channel must be executed as $k$ independent OS processes.*  

---

## Table of Contents

1. [What We Have To Do](#1-what-we-have-to-do)
   - [Problem Statement & Process Architecture Constraint](#11-problem-statement--process-architecture-constraint)
   - [Core Deliverables](#12-core-deliverables)
   - [Sender-Receiver Architecture](#13-sender-receiver-architecture)
2. [Multi-Process Concurrency & IPC Architecture](#2-multi-process-concurrency--ipc-architecture)
   - [Why CDMA Must Not Be a Monolithic Standalone Process](#21-why-cdma-must-not-be-a-monolithic-standalone-process)
   - [Process Isolation and Memory Space Decoupling](#22-process-isolation-and-memory-space-decoupling)
   - [Inter-Process Communication (IPC) Mechanisms](#23-inter-process-communication-ipc-mechanisms)
   - [Lockstep Synchronous Slotted Protocol](#24-lockstep-synchronous-slotted-protocol)
   - [Process Lifecycle and Handshake Sequence](#25-process-lifecycle-and-handshake-sequence)
3. [Core Concepts & Mathematical Theory](#3-core-concepts--mathematical-theory)
   - [The Problem of Multiple Access](#31-the-problem-of-multiple-access)
   - [Channelization Protocols: FDMA vs. TDMA vs. CDMA](#32-channelization-protocols-fdma-vs-tdma-vs-cdma)
   - [Direct Sequence Spread Spectrum (DSSS)](#33-direct-sequence-spread-spectrum-dsss)
   - [Walsh Functions and Hadamard Matrices](#34-walsh-functions-and-hadamard-matrices)
   - [Sylvester’s Recursive Construction](#35-sylvesters-recursive-construction)
   - [Mathematical Proof of Mutual Orthogonality](#36-mathematical-proof-of-mutual-orthogonality)
   - [Bipolar Non-Return-to-Zero (NRZ) Mapping](#37-bipolar-non-return-to-zero-nrz-mapping)
   - [Multi-Station Spreading (Kronecker Product)](#38-multi-station-spreading-kronecker-product)
   - [Linear Superposition in the Shared Medium](#39-linear-superposition-in-the-shared-medium)
   - [Correlator Receiver & Despreading Inner Product](#310-correlator-receiver--despreading-inner-product)
   - [Proof of Perfect Reconstruction (Zero Multi-User Interference)](#311-proof-of-perfect-reconstruction-zero-multi-user-interference)
   - [Handling Silent / Idle Stations](#312-handling-silent--idle-stations)
   - [Processing Gain and Jammer Rejection](#313-processing-gain-and-jammer-rejection)
   - [Channel Impairments: AWGN Noise and the Q-Function](#314-channel-impairments-awgn-noise-and-the-q-function)
   - [The Near-Far Problem and Power Control](#315-the-near-far-problem-and-power-control)
4. [Things We Need to Know (Conceptual Walkthrough)](#4-things-we-need-to-know-conceptual-walkthrough)
   - [Chip Time vs. Bit Time](#41-chip-time-vs-bit-time)
   - [Vector Space Representation](#42-vector-space-representation)
   - [Numerical Step-by-Step Example (4 Stations)](#43-numerical-step-by-step-example-4-stations)
5. [Software System Architecture](#5-software-system-architecture)
   - [Module Decomposition](#51-module-decomposition)
   - [Data Flow Diagram](#52-data-flow-diagram)
   - [State Machine Transitions](#53-state-machine-transitions)
6. [Rich Terminal Dashboard Architecture](#6-rich-terminal-dashboard-architecture)
7. [Benchmarking & Empirical Validation](#7-benchmarking--empirical-validation)
8. [Analysis of Generated Figures](#8-analysis-of-generated-figures)
9. [Comprehensive Viva Questions & Answers](#9-comprehensive-viva-questions--answers)

---

## 1. What We Have To Do

### 1.1 Problem Statement & Process Architecture Constraint
From the assignment prompt and supplementary specification (`.txt`):
> *CSE/PC/B/S/314 Computer Networks Lab — Assignment 4: Implement CDMA with Walsh code.*  
> *Use the same sender-receiver design as previous assignments.*  
> *In this assignment you have to implement CDMA for multiple access of a common channel by $n$ stations. Each sender uses a unique code word, given by the Walsh set, to encode its data, send it across the channel, and then perfectly reconstruct the data at $n$ stations.*  
> **ARCHITECTURAL MANDATE (`.txt`)**:  
> *"CDMA shouldn't be a single standalone process, if there are $k$ no of stations sharing the same channel there should be $k$ processes."*

### 1.2 Core Deliverables
1. **Multi-Process Architecture**: Exactly $k$ independent OS worker processes are spawned to represent the $k$ stations, each with its own virtual memory space, process identifier (PID), transmitter state, and receiver state.
2. **Inter-Process Communication (IPC)**: Duplex IPC Pipes and TCP Sockets connect the station processes to the shared Channel hub.
3. **Walsh-Hadamard Code Generator**: Recursively construct $H_N$ matrices where $N = 2^{\lceil \log_2(k) \rceil}$, verify mutual orthogonality ($H \cdot H^T = N \cdot I_N$), and allocate unique orthogonal codewords $W_i$ to each station $i$.
4. **Sender-Receiver Design Pattern**:
   - **Sender**: Converts binary data/ASCII characters into bipolar pulses ($+1, -1, 0$), spreads each bit with the assigned Walsh codeword of length $N$ to produce chip vectors $s_i$.
   - **Common Channel**: Models the linear superposition $C = \sum_{i=0}^{k-1} s_i$ over a shared physical medium, with support for optional Additive White Gaussian Noise (AWGN).
   - **Receiver**: Implements an inner-product matched filter correlator $\hat{d}_j = \frac{1}{N} (C \cdot W_j)$ to despread and recover the original transmitted bits and text streams without cross-talk.
5. **Live Terminal Dashboard using `rich`**: An interactive UI displaying allocated Walsh codes, real-time chip waveforms, station transmission matrices, dot product arithmetic, cumulative reconstructed message streams, and **active OS Process IDs (PIDs)**.
6. **Automated Benchmarking Suite**: Systematic evaluation of station scalability ($n = 2 \to 64$), SNR sensitivity sweeps ($-10 \text{ dB} \to +16 \text{ dB}$), empirical vs. theoretical Bit Error Rate (BER), and CSV data exports.
7. **Publication-Grade Visualization**: Generation of 8 scientific PNG plots illustrating orthogonality heatmaps, time-domain waveforms, correlator peaks, BER waterfall curves, and processing gain.
8. **Detailed Test Suite & Documentation**: 20 automated unit and integration tests covering mathematical guarantees, silent stations, variable message lengths, AWGN noise tolerance, and **multi-process isolation**.

### 1.3 Sender-Receiver Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      SHARED COMMON CHANNEL HUB                          │
│                     (Channel Process / Server)                          │
│                     C[k] = sum(s_i[k]) + eta[k]                         │
└─────────────────────────────────────────────────────────────────────────┘
        ▲                                                          │
        │ Transmitted Chip Vectors (s_i)                           │ Broadcast Composite (C)
        │ via Duplex IPC Pipe / Socket                             │ via Duplex IPC Pipe / Socket
        ▼                                                          ▼
┌───────────────────────────┐                  ┌───────────────────────────┐
│ STATION PROCESS 0 (PID p0)│                  │ STATION PROCESS 1 (PID p1)│
│  +─────────────────────+  │                  │  +─────────────────────+  │
│  |     SENDER 0        |  │                  │  |     SENDER 1        │  │
│  | Bit: b_0 in {0,1}   |  │                  │  | Bit: b_1 in {0,1}   |  │
│  | Bipolar: d_0 in {±1}|  │                  │  | Bipolar: d_1 in {±1}|  │
│  | Chips: s_0=d_0*W_0  |  │                  │  | Chips: s_1=d_1*W_1  │  │
│  +─────────────────────+  │                  │  +─────────────────────+  │
│  +─────────────────────+  │                  │  +─────────────────────+  │
│  |    RECEIVER 0       |  │                  │  |    RECEIVER 1       |  │
│  | In: Composite C     |  │                  │  | In: Composite C     |  |
│  | Walsh: W_0          |  │                  │  | Walsh: W_1          |  |
│  | Correlate: C · W_0  |  │                  │  | Correlate: C · W_1  |  │
│  | Decision: b_hat_0   |  │                  │  | Decision: b_hat_1   |  │
│  +─────────────────────+  │                  │  +─────────────────────+  │
└───────────────────────────┘                  └───────────────────────────┘
```

---

## 2. Multi-Process Concurrency & IPC Architecture

### 2.1 Why CDMA Must Not Be a Monolithic Standalone Process
In a physical network:
1. **Physical Decentralization**: Stations (e.g. mobile handsets, cellular basestations, satellite ground terminals) are completely independent physical computers located in disparate physical locations. They do not share CPU registers, thread pools, or RAM.
2. **No Shared State**: Station $A$ has no direct access to the transmission buffer, bit queue, or internal state of Station $B$.
3. **Asynchronous Execution**: In a realistic system, each node runs its own independent operating system scheduling loop.
4. **Authentic Simulation**: Simulating CDMA inside a single monolithic Python loop with a list of stations does not capture true operating system concurrency, process scheduling, memory isolation, or inter-process communication overhead.

Therefore, our implementation adheres strictly to the rule:
$$\text{If there are } k \text{ stations sharing the channel, there are } k \text{ independent OS processes.}$$

### 2.2 Process Isolation and Memory Space Decoupling
By instantiating each station as an independent OS process (`multiprocessing.Process`):
- **Separate Address Spaces**: Each station process possesses an independent Virtual Memory space with its own private heap, stack, and file descriptors.
- **True Parallelism**: On multi-core processors, the OS kernel schedules the station processes across physical CPU cores simultaneously, avoiding the Python Global Interpreter Lock (GIL) limitations.
- **Failure Isolation**: A crash or exception in Station $i$ does not corrupt the memory or execution state of Station $j$.

### 2.3 Inter-Process Communication (IPC) Mechanisms
To model the transmission of physical signals between the isolated station processes and the common channel, we provide two IPC architectures:

#### Mechanism 1: Duplex IPC Pipes (`multiprocessing.Pipe`)
- Used by the master `MultiProcessCDMASimulation` and the Rich terminal dashboard.
- Provides point-to-point, bidirectional OS file descriptor pipes connecting each child process to the Channel orchestrator.
- High throughput, low latency, and zero network configuration required.

#### Mechanism 2: BSD TCP Sockets (`socket.AF_INET, socket.SOCK_STREAM`)
- Used for standalone multi-terminal operation.
- Allows running `python3 channel.py --serve --port 9000` in Terminal 1, and connecting independent station processes from separate terminal windows (`python3 station.py --connect --id 0`, `python3 station.py --connect --id 1`, etc.).
- Demonstrates true distributed networking over the TCP/IP stack.

### 2.4 Lockstep Synchronous Slotted Protocol
Synchronous CDMA requires all stations to transmit chips simultaneously in each bit slot $t$. To achieve synchronous lockstep across $k$ autonomous processes, the Channel Hub implements a **Rendezvous Synchronization Barrier**:

```
Channel Process (Hub)                   Station Process 0..k-1
       │                                         │
       ├──── REQUEST_CHIPS (Slot t) ────────────►│ (Each process encodes bit)
       │                                         │ (Computes s_i = d_i * W_i)
       │◄─── CHIPS s_i [k vectors] ──────────────┤ (Sends chip vector)
       │                                         │
[ Channel sums C = sum(s_i) + AWGN ]             │
       │                                         │
       ├──── BROADCAST_COMPOSITE C ─────────────►│ (Each process receives C)
       │                                         │ (Computes Y_i = C · W_i)
       │                                         │ (Decodes bit b_hat_i)
       │◄─── DECODED Confirmation ───────────────┤ (Sends decoded status)
       │                                         │
[ Telemetry logged for Dashboard ]               │
       │                                         │
Slot t advances to t + 1                         │
```

### 2.5 Process Lifecycle and Handshake Sequence
1. **Spawn Phase**: The orchestrator invokes `multiprocessing.Process(target=station_process_worker, args=(...))` for stations $0 \dots k-1$.
2. **Handshake Phase**: Each child process queries `os.getpid()` and sends a `READY` message through its pipe. The orchestrator records the child PIDs.
3. **Execution Phase**: Slotted transmissions proceed in synchronous lockstep.
4. **Termination Phase**: The orchestrator sends a `TERMINATE` message. Each child process generates its local verification report (`is_perfect`, `errors`, `ber`), transmits it back to the channel, closes its IPC descriptors, and exits cleanly. The orchestrator joins all processes (`proc.join()`).

---

## 3. Core Concepts & Mathematical Theory

### 3.1 The Problem of Multiple Access
In any telecommunications system, multiple nodes share a common physical transmission medium. If multiple nodes transmit simultaneously on an unmanaged channel:
1. Signal voltages sum up linearly at the receiving antennas.
2. In classical contention protocols (ALOHA, CSMA), this causes a **collision**, destroying packet headers and payloads.
3. Medium Access Control (MAC) protocols are designed to allocate access fairly and efficiently.

### 3.2 Channelization Protocols: FDMA vs. TDMA vs. CDMA

| Parameter | Frequency Division (FDMA) | Time Division (TDMA) | Code Division (CDMA) |
|---|---|---|---|
| **Sharing Domain** | Frequency Spectrum | Time Slots | Orthogonal Mathematical Codes |
| **Bandwidth Allocation** | Each user gets a narrow slice $B/n$ | Users get entire bandwidth $B$ during slot | Every user transmits over entire bandwidth $B$ continuously |
| **Transmission Timing** | Continuous | Intermittent (bursts) | Continuous |
| **Process Model** | 1 transceiver process per freq channel | 1 transceiver active per time slot | **$k$ concurrent processes sharing same channel** |
| **Capacity Limitation** | Strictly limited by hardware frequency filters | Strictly limited by available time slots | Soft capacity: limited by interference floor |
| **Fading & Jamming Resistance** | Poor (narrowband fading wipes out channel) | Moderate | Excellent (wideband spread spectrum processing gain) |

### 3.3 Direct Sequence Spread Spectrum (DSSS)
CDMA is fundamentally built on **Direct Sequence Spread Spectrum (DSSS)**.
In DSSS:
- A narrowband information signal of bit duration $T_b$ and data rate $R_b = 1/T_b$ is multiplied by a high-rate pseudorandom or orthogonal sequence called a **chip sequence** with chip duration $T_c \ll T_b$.
- The ratio of bit duration to chip duration is called the **Spreading Factor (SF)** or **Processing Gain ($N$)**:
  $$N = \frac{T_b}{T_c} = \frac{R_c}{R_b}$$
- Multiplying the data signal by the chip sequence expands the occupied bandwidth from $B \approx R_b$ to a spread bandwidth $W \approx R_c = N \cdot R_b$.
- The power spectral density drops below the thermal noise floor, rendering the transmission covert and resilient against narrow-band jamming.

### 3.4 Walsh Functions and Hadamard Matrices
Walsh functions, discovered by Joseph L. Walsh in 1923, form a complete orthonormal basis on the interval $[0, 1)$ taking values in $\{-1, +1\}$.
Discrete Walsh codewords correspond to the rows of **Hadamard matrices**.

A Hadamard matrix $H_N$ of order $N$ is an $N \times N$ matrix of entries $\pm 1$ whose rows (and columns) are mutually orthogonal:
$$H_N \cdot H_N^T = N \cdot I_N$$
where $I_N$ is the $N \times N$ identity matrix.

### 3.5 Sylvester’s Recursive Construction
In 1867, J. J. Sylvester introduced a recursive construction that generates Hadamard matrices of order $2^k$ for any non-negative integer $k$:

$$H_1 = [1]$$

$$H_2 = \begin{bmatrix} 1 & 1 \\ 1 & -1 \end{bmatrix}$$

$$H_{2N} = \begin{bmatrix} H_N & H_N \\ H_N & -H_N \end{bmatrix} = H_2 \otimes H_N$$
where $\otimes$ denotes the Kronecker tensor product.

For order $N = 4$:
$$H_4 = \begin{bmatrix}
H_2 & H_2 \\
H_2 & -H_2
\end{bmatrix} =
\begin{bmatrix}
+1 & +1 & +1 & +1 \\
+1 & -1 & +1 & -1 \\
+1 & +1 & -1 & -1 \\
+1 & -1 & -1 & +1
\end{bmatrix}$$

### 3.6 Mathematical Proof of Mutual Orthogonality

#### Theorem:
*Any two distinct rows $W_i$ and $W_j$ ($i \neq j$) of Sylvester’s Hadamard matrix $H_N$ are orthogonal, and the inner product of any row with itself equals $N$.*

#### Proof by Mathematical Induction:
**Base Case ($k=1, N=2$):**
$$H_2 = \begin{bmatrix} W_0 \\ W_1 \end{bmatrix} = \begin{bmatrix} +1 & +1 \\ +1 & -1 \end{bmatrix}$$
- Self inner product:
  $$W_0 \cdot W_0 = (+1)(+1) + (+1)(+1) = 1 + 1 = 2$$
  $$W_1 \cdot W_1 = (+1)(+1) + (-1)(-1) = 1 + 1 = 2$$
- Cross inner product:
  $$W_0 \cdot W_1 = (+1)(+1) + (+1)(-1) = 1 - 1 = 0$$
Hence the base case holds.

**Inductive Step:**
Assume that $H_N \cdot H_N^T = N \cdot I_N$ holds for order $N = 2^k$.
Consider $H_{2N}$:
$$H_{2N} = \begin{bmatrix} H_N & H_N \\ H_N & -H_N \end{bmatrix}$$
Compute the Gramian matrix $G_{2N} = H_{2N} \cdot H_{2N}^T$:
$$G_{2N} = \begin{bmatrix} H_N & H_N \\ H_N & -H_N \end{bmatrix} \begin{bmatrix} H_N^T & H_N^T \\ H_N^T & -H_N^T \end{bmatrix}$$
Performing block matrix multiplication:
$$G_{2N} = \begin{bmatrix}
H_N H_N^T + H_N H_N^T & H_N H_N^T - H_N H_N^T \\
H_N H_N^T - H_N H_N^T & H_N H_N^T + (-H_N)(-H_N^T)
\end{bmatrix}$$
Substitute the inductive hypothesis $H_N H_N^T = N \cdot I_N$:
$$G_{2N} = \begin{bmatrix}
N I_N + N I_N & N I_N - N I_N \\
N I_N - N I_N & N I_N + N I_N
\end{bmatrix} = \begin{bmatrix}
2N I_N & 0 \\
0 & 2N I_N
\end{bmatrix} = 2N \cdot I_{2N}$$
Thus, by mathematical induction, $H_M \cdot H_M^T = M \cdot I_M$ holds for all $M = 2^k, k \in \mathbb{N}$. $\blacksquare$

### 3.7 Bipolar Non-Return-to-Zero (NRZ) Mapping
In unipolar binary representation ($0$ and $1$), arithmetic summation is not symmetric around zero:
$$\sum 0 \cdot W_i = 0, \quad \sum 1 \cdot W_i = W_i$$
This would introduce a non-zero DC bias and prevent linear orthogonality from cancelling silent or competing signals.

In CDMA, we employ **bipolar NRZ modulation**:
$$\text{Data Bit } b_i \longrightarrow \text{Bipolar Symbol } d_i = \begin{cases}
+1, & \text{if } b_i = 1 \\
-1, & \text{if } b_i = 0 \\
0, & \text{if station } i \text{ is silent / idle}
\end{cases}$$

### 3.8 Multi-Station Spreading (Kronecker Product)
For station $i$, the transmitted chip sequence $s_i$ over a bit period $T_b$ is the scalar-vector product of its bipolar symbol $d_i$ with its allocated Walsh codeword $W_i$:
$$s_i = d_i \cdot W_i = [d_i W_i[0], d_i W_i[1], \dots, d_i W_i[N-1]]$$

### 3.9 Linear Superposition in the Shared Medium
When $k$ station processes transmit simultaneously over a common linear medium, their signals superimpose linearly:
$$C = \sum_{i=0}^{k-1} s_i = \sum_{i=0}^{k-1} d_i \cdot W_i$$
In chip vector form:
$$C[m] = \sum_{i=0}^{k-1} d_i \cdot W_i[m], \quad \forall m \in \{0, 1, \dots, N-1\}$$

### 3.10 Correlator Receiver & Despreading Inner Product
To recover the information bit sent by station $j$, the receiver process for station $j$ multiplies the received channel signal vector $C$ by its locally stored Walsh codeword $W_j$ and integrates (sums) over code length $N$:
$$Y_j = C \cdot W_j = \sum_{m=0}^{N-1} C[m] \cdot W_j[m]$$

### 3.11 Proof of Perfect Reconstruction (Zero Multi-User Interference)
Substitute $C$ into $Y_j$:
$$Y_j = \left( \sum_{i=0}^{k-1} d_i \cdot W_i \right) \cdot W_j = \sum_{i=0}^{k-1} d_i \cdot (W_i \cdot W_j)$$
Split the summation:
$$Y_j = d_j \cdot (W_j \cdot W_j) + \sum_{i \neq j} d_i \cdot (W_i \cdot W_j)$$
From the orthogonality theorem:
1. $W_j \cdot W_j = N$
2. $W_i \cdot W_j = 0$ for all $i \neq j$

Therefore:
$$Y_j = d_j \cdot N + 0 = N \cdot d_j$$

Normalizing by code length $N$:
$$\hat{d}_j = \frac{Y_j}{N} = \frac{N \cdot d_j}{N} = d_j$$

Decision Rule:
$$\hat{b}_j = \begin{cases}
1, & \text{if } \hat{d}_j > 0.5 \\
0, & \text{if } \hat{d}_j < -0.5 \\
\text{None (Idle)}, & \text{if } |\hat{d}_j| \le 0.5
\end{cases}$$

Since $\hat{d}_j = d_j$ identically, **$\hat{b}_j = b_j$ without error across all $k$ independent processes**. $\blacksquare$

### 3.12 Handling Silent / Idle Stations
When a station process has no data:
- It transmits $d_k = 0 \implies s_k = [0, \dots, 0]$.
- It contributes zero energy to the channel sum.
- At receiver $k$, $\hat{d}_k = 0$, decoding as Idle without causing interference to other active station processes.

### 3.13 Processing Gain and Jammer Rejection
Processing Gain:
$$G_p = \frac{R_c}{R_b} = N \implies G_{p,\text{dB}} = 10 \log_{10}(N)$$
Suppresses narrowband jammers and uncoordinated interference by a factor of $1/N$.

### 3.14 Channel Impairments: AWGN Noise and the Q-Function
In realistic channels with AWGN $\eta \sim \mathcal{N}(0, \sigma^2)$:
$$Y_j = N d_j + \eta \cdot W_j \implies \hat{d}_j = d_j + \frac{\eta \cdot W_j}{N}$$
The despreading process reduces noise variance by $N$:
$$\sigma_{\text{eff}}^2 = \frac{\sigma^2}{N}$$
The Bit Error Rate is:
$$P_b = Q\left( \sqrt{\text{SNR}_{\text{linear}}} \right) = Q\left( \sqrt{\frac{2 E_b}{N_0}} \right)$$

### 3.15 The Near-Far Problem and Power Control
In synchronous CDMA with Walsh codes, zero cross-correlation eliminates the near-far problem in downlink communication. In asynchronous CDMA (where time delays destroy orthogonality), fast closed-loop power control is mandatory to equalize received power.

---

## 4. Things We Need to Know (Conceptual Walkthrough)

### 4.1 Chip Time vs. Bit Time
- **Bit Period ($T_b$)**: Duration to transmit one data bit.
- **Chip Period ($T_c$)**: Duration of a single Walsh chip.
- $T_b = N \cdot T_c$.

### 4.2 Vector Space Representation
The $N$ Walsh codewords $\{W_0, \dots, W_{N-1}\}$ form an orthonormal basis of $\mathbb{R}^N$. Each station process transmits along its dedicated orthogonal axis. The channel computes the vector sum, and each receiver projectively extracts its component via dot product.

### 4.3 Numerical Step-by-Step Example (4 Stations)
Let $k = 4$ stations with $N = 4$ Walsh codes:
- $W_0 = [+1, +1, +1, +1]$
- $W_1 = [+1, -1, +1, -1]$
- $W_2 = [+1, +1, -1, -1]$
- $W_3 = [+1, -1, -1, +1]$

Bits: $b = [1, 0, 1, 0] \implies d = [+1, -1, +1, -1]$.
Spread:
- $s_0 = [+1, +1, +1, +1]$
- $s_1 = [-1, +1, -1, +1]$
- $s_2 = [+1, +1, -1, -1]$
- $s_3 = [-1, +1, +1, -1]$

Channel Superposition:
$$C = s_0 + s_1 + s_2 + s_3 = [0, +4, 0, 0]$$

Despreading:
- Process 0: $C \cdot W_0 = 4 \implies \hat{d}_0 = +1.0 \implies \text{Bit 1 [MATCH]}$
- Process 1: $C \cdot W_1 = -4 \implies \hat{d}_1 = -1.0 \implies \text{Bit 0 [MATCH]}$
- Process 2: $C \cdot W_2 = 4 \implies \hat{d}_2 = +1.0 \implies \text{Bit 1 [MATCH]}$
- Process 3: $C \cdot W_3 = -4 \implies \hat{d}_3 = -1.0 \implies \text{Bit 0 [MATCH]}$

---

## 5. Software System Architecture

### 5.1 Module Decomposition
1. **`walsh.py`**: Sylvester Hadamard generator and orthogonality engine.
2. **`channel.py`**: Shared superposition medium and standalone TCP socket server.
3. **`station.py`**: Station, Sender, Receiver classes, `station_process_worker` target function for OS processes, and TCP socket client.
4. **`simulation.py`**: `MultiProcessCDMASimulation` managing $k$ OS child processes via IPC Pipes, plus lightweight `CDMASimulation`.
5. **`dashboard.py`**: Live Rich terminal dashboard displaying waveforms, sparklines, and active OS PIDs.
6. **`benchmark.py`**: Automated performance test engine.
7. **`plot_results.py`**: 8-figure Matplotlib publication generator.
8. **`test_cdma.py`**: Automated test suite with 20 unit and multi-process tests.
9. **`codes.py`**: Master CLI application and interactive menu.

---

## 6. Rich Terminal Dashboard Architecture
Visualizes the multi-process CDMA network in real time:
- Title panel showing active station process count and Channel status.
- Walsh Code Table displaying station IDs, **OS PIDs**, allocated codewords, and orthogonality status.
- Shared Channel Panel displaying composite vector $C$, chip waveform bars, and energy sparklines.
- Spreading Matrix showing each process's PID, transmitted bit, bipolar value, spread chips, dot product, decoded bit, match indicator, and reconstructed string.
- Event log displaying child process lifecycle events and synchronization handshakes.

---

## 7. Benchmarking & Empirical Validation

### Scalability Benchmark ($n = 2 \to 64$ Stations)
| Stations ($n$) | Code Length ($N$) | Total Bits | Time (s) | Bit Rate (bps) | Errors | BER | Status |
|---|---|---|---|---|---|---|---|
| **2** | 2 | 1,000 | 0.005 | 206,533 | 0 | 0.0000 | 100% Perfect |
| **4** | 4 | 2,000 | 0.007 | 298,675 | 0 | 0.0000 | 100% Perfect |
| **8** | 8 | 4,000 | 0.013 | 319,395 | 0 | 0.0000 | 100% Perfect |
| **16** | 16 | 8,000 | 0.020 | 401,129 | 0 | 0.0000 | 100% Perfect |
| **32** | 32 | 16,000 | 0.063 | 403,975 | 0 | 0.0000 | 100% Perfect |
| **64** | 64 | 32,000 | 0.127 | 404,181 | 0 | 0.0000 | 100% Perfect |

---

## 8. Analysis of Generated Figures
1. **`fig1_walsh_orthogonal_matrix.png`**: Walsh matrix $H_8$ and Gramian $G = 8 I_8$.
2. **`fig2_cdma_encoding_superposition.png`**: Step waveforms of station signals and composite $C(t)$.
3. **`fig3_despreading_correlation.png`**: Correlator dot product peaks demonstrating zero MUI.
4. **`fig4_ber_vs_snr_awgn.png`**: Empirical Monte Carlo BER vs. theoretical $Q(\sqrt{\text{SNR}})$.
5. **`fig5_throughput_vs_stations.png`**: Multi-user capacity scaling from 2 to 64 stations.
6. **`fig6_processing_gain_analysis.png`**: Processing gain $G_p = 10 \log_{10}(N)$ dB vs. codeword length.
7. **`fig7_multi_station_constellation.png`**: Composite channel amplitude histograms confirming Central Limit Theorem.
8. **`fig8_combined_summary.png`**: Comprehensive 4-panel executive lab summary.

---

## 9. Comprehensive Viva Questions & Answers

### Q1: Why must CDMA with $k$ stations be implemented as $k$ separate processes?
**Answer**: In real computer networks, transmitting stations are autonomous, physically decentralized hardware nodes. They have completely isolated memory spaces, independent clocks, and private CPU execution environments. Running $k$ separate processes models authentic process isolation, prevents invalid shared memory shortcuts, and demonstrates realistic Inter-Process Communication (IPC) across a shared medium.

### Q2: How do the $k$ station processes synchronize with the channel in each slot?
**Answer**: They utilize a rendezvous lockstep protocol over duplex IPC pipes (or sockets). In each bit slot, the Channel hub requests chips from all $k$ processes, collects their chip vectors, computes the linear superposition $C$, broadcasts $C$ back to all $k$ processes, and receives their decoded acknowledgments before advancing the clock.

### Q3: What is the difference between Walsh codes and Gold codes?
**Answer**: Walsh codes have perfect zero cross-correlation at zero time offset ($\tau = 0$), making them ideal for synchronous downlink transmission. However, when shifted ($\tau \neq 0$), their cross-correlation is poor. Gold codes are pseudorandom sequences designed for asynchronous uplink CDMA; their cross-correlation is not zero, but it remains bounded by small values across all possible time delays.

### Q4: Prove mathematically why there is zero cross-talk between stations in synchronous CDMA.
**Answer**: $C = \sum_{i=0}^{k-1} d_i W_i$. When correlated with $W_j$:
$$Y_j = C \cdot W_j = \sum_{i=0}^{k-1} d_i (W_i \cdot W_j) = d_j (W_j \cdot W_j) + \sum_{i \neq j} d_i (0) = N d_j$$
Dividing by $N$ gives $\hat{d}_j = d_j$. Multi-User Interference (MUI) is strictly identically zero.

### Q5: How does bipolar NRZ encoding prevent DC bias?
**Answer**: Unipolar bits ($0$ and $1$) lack mathematical symmetry around zero. Bipolar NRZ maps $1 \to +1$, $0 \to -1$, and silent to $0$. This balances signal energy symmetrically around zero, enabling linear cancellation during inner product computation.

### Q6: What is Processing Gain and why does it matter?
**Answer**: Processing Gain $G_p = T_b / T_c = N$ (or $10 \log_{10}(N)$ dB) measures the bandwidth expansion factor. It quantifies the system's ability to suppress narrowband jamming and operate in low SNR channels.

### Q7: What is the Near-Far Problem and how is it mitigated?
**Answer**: The near-far problem occurs when a nearby station's strong signal drowns out a distant station's weak signal due to non-zero cross-correlation. In synchronous CDMA with orthogonal Walsh codes, cross-correlation is zero so the near-far problem is eliminated. In asynchronous CDMA, fast closed-loop power control equalizes received powers at the basestation.

### Q8: What happens when an idle/silent station is part of the CDMA network?
**Answer**: An idle station outputs $d_k = 0$, producing chip vector $[0, \dots, 0]$. It injects zero energy into the channel. At the receiver, its inner product is $0$, which falls within the threshold dead-band $[-0.5, +0.5]$, decoding correctly as Idle without affecting active users.

### Q9: How does thermal noise (AWGN) affect CDMA despreading?
**Answer**: Adding noise $\eta$ to $C$ produces $Y_j = N d_j + \eta \cdot W_j$. Normalizing by $N$ yields $\hat{d}_j = d_j + \frac{\eta \cdot W_j}{N}$. The variance of the noise on $\hat{d}_j$ is reduced by $N$ ($\sigma_{\text{eff}}^2 = \sigma^2 / N$), preserving the theoretical BPSK BER curve $Q(\sqrt{2 E_b / N_0})$.

### Q10: What IPC mechanisms can be used for multi-process CDMA, and what are their trade-offs?
**Answer**:
- **Duplex Pipes / Unix Domain Sockets**: Fast, kernel-mediated file descriptors, zero network overhead; ideal for local multi-process simulation.
- **TCP Sockets**: Network-capable, allows stations to run on different physical machines or separate terminal windows, slightly higher protocol overhead.
- **Shared Memory (POSIX shm)**: Fastest raw data transfer, but requires explicit semaphores or mutexes to prevent race conditions during slot updates.
