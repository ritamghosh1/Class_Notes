# Channel Module Theory — `channel.py`

> **File**: `channel.py`  
> **Class**: `Channel`  
> **Function**: `run_socket_channel_server()`  
> **Role**: Shared CDMA broadcast medium & IPC superposition hub  

---

## 1. What This Module Does

`channel.py` models the shared physical medium connecting all stations in the CDMA network. In a multi-process architecture, the Channel acts as an **IPC Superposition Hub**:
- Multiplexes transmitted chip vectors arriving from $k$ independent station processes.
- Computes linear superposition $C = \sum_{i=0}^{k-1} s_i$.
- Injects optional Additive White Gaussian Noise (AWGN).
- Broadcasts the composite signal vector back to all $k$ station processes.
- Provides a standalone TCP socket server (`run_socket_channel_server()`) for multi-terminal execution.

---

## 2. Mathematical Model

### 2.1 Linear Superposition
For $k$ independent station processes transmitting simultaneously:
$$C[m] = \sum_{i=0}^{k-1} s_i[m], \quad \forall m \in \{0, \dots, N-1\}$$

### 2.2 Additive White Gaussian Noise (AWGN)
$$C_{\text{noisy}} = C + \eta, \quad \eta[m] \sim \mathcal{N}(0, \sigma^2)$$
$$\sigma^2 = \frac{P_{\text{signal}}}{10^{\text{SNR}_{\text{dB}} / 10}}$$

---

## 3. IPC Architecture & Standalone Socket Server

```
Station Process 0 (PID P0) ──► [Pipe / Socket] ──┐
Station Process 1 (PID P1) ──► [Pipe / Socket] ──┼──► [ Channel Process / Hub ]
Station Process 2 (PID P2) ──► [Pipe / Socket] ──┤     1. Sums C = sum(s_i)
Station Process 3 (PID P3) ──► [Pipe / Socket] ──┘     2. Adds AWGN(SNR)
                                                       3. Broadcasts C back to all pipes
```

### Standalone Server CLI:
```bash
python3 channel.py --serve --port 9000 --stations 4
```
Listens on TCP port 9000, accepts connections from 4 independent station terminal processes, distributes Walsh codes, and coordinates synchronous slot transmissions.
