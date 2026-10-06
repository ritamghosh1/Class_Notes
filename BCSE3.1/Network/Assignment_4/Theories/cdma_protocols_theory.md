# CDMA Protocols & Multiple Access Theory — `cdma_protocols_theory.md`

> **Topic**: Code Division Multiple Access Protocols, Spreading Codes, and Channelization  
> **Course**: CSE/PC/B/S/314 Computer Networks Lab  

---

## 1. Multiple Access Taxonomy

Medium Access Control (MAC) protocols govern access to shared communication channels:

```
                          Medium Access Control (MAC)
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
Contention-Based (Random)     Controlled Access              Channelization
  - ALOHA                       - Polling                      - FDMA (Frequency)
  - CSMA                        - Token Ring                   - TDMA (Time)
  - CSMA/CD (Assignment 3)      - Reservation                  - CDMA (Code, Assignment 4)
  - CSMA/CA (Wi-Fi)                                            - SDMA (Space)
```

---

## 2. Theoretical Principles of CDMA

### 2.1 Principle of Orthogonality
In linear algebra, two non-zero vectors $\mathbf{u}$ and $\mathbf{v}$ in an inner product space $\mathbb{R}^N$ are **orthogonal** if their inner product is zero:
$$\langle \mathbf{u}, \mathbf{v} \rangle = \mathbf{u} \cdot \mathbf{v} = 0$$

In CDMA:
- Each communication channel is assigned a unique basis vector (codeword) $\mathbf{w}_i$.
- When all signals are added together on the channel, they occupy the same space simultaneously:
  $$\mathbf{C} = \sum_{i=1}^n d_i \mathbf{w}_i$$
- When the receiver computes the inner product with basis vector $\mathbf{w}_j$:
  $$\langle \mathbf{C}, \mathbf{w}_j \rangle = \sum_{i=1}^n d_i \langle \mathbf{w}_i, \mathbf{w}_j \rangle = d_j \|\mathbf{w}_j\|^2$$
- The contribution from all other users ($i \neq j$) is completely eliminated because their projection onto $\mathbf{w}_j$ is zero.

---

## 3. Comparison of Spreading Sequences

| Sequence Type | Orthogonality at Zero Lag ($\tau = 0$) | Cross-Correlation at Non-Zero Lag ($\tau \neq 0$) | Auto-Correlation Properties | Primary Usage |
|---|---|---|---|---|
| **Walsh-Hadamard Codes** | **Strictly 0 (Perfect)** | High / Non-zero | Poor off-peak properties | **Synchronous Downlink** (Base Station to Mobiles) |
| **m-Sequences (Maximal Length)** | Near-zero ($1/N$) | Bounded cross-correlation | Excellent delta-like auto-correlation | Channel sounding, synchronization |
| **Gold Codes** | Near-zero | Bounded 3-valued cross-correlation | Good auto-correlation | **Asynchronous Uplink**, GPS L1 C/A |
| **Kasami Codes** | Near-zero | Optimal Welch lower bound | Very good auto-correlation | Dense multi-user asynchronous networks |

---

## 4. Synchronous vs. Asynchronous CDMA

### 4.1 Synchronous CDMA (Implemented in this Assignment)
- All transmitters are locked to a common clock reference.
- Every station begins its chip sequence at the exact same physical instant ($t = 0$).
- Because propagation delays are either negligible or compensated via timing advance:
  $$\tau_{ij} = 0, \quad \forall i, j$$
- Under zero time shift, Walsh codes maintain perfect mutual orthogonality, completely eliminating Multi-User Interference (MUI).

### 4.2 Asynchronous CDMA
- Mobile stations transmit autonomously without microsecond time alignment.
- Signals arrive with variable fractional chip delays $\tau_i \in [0, T_c)$.
- Orthogonality is lost; cross-correlation is non-zero, generating multi-access noise floor:
  $$\text{SNR}_{\text{eff}} \approx \frac{1}{\frac{n - 1}{3N} + \frac{N_0}{2E_b}}$$
- Requires spread spectrum processing gain $N \gg 1$ and fast power control.
