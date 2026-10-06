# Station Module Theory — `station.py`

> **File**: `station.py`  
> **Classes**: `Station`, `Sender`, `Receiver`  
> **Functions**: `station_process_worker()`, `run_socket_station_client()`  
> **Role**: Independent OS station process, modulation, matched filtering, and IPC  

---

## 1. What This Module Does

`station.py` models the network nodes in the CDMA system. Conforming directly to:
1. The **Sender-Receiver Design Pattern** from previous assignments:
   - Dedicated `Sender` unit (transmitter)
   - Dedicated `Receiver` unit (correlator matched filter)
2. The **Process Architecture Constraint**:
   - `station_process_worker()`: Top-level entrypoint for independent OS child processes communicating via IPC Pipes.
   - `run_socket_station_client()`: Standalone TCP socket client allowing stations to be executed in separate terminal windows.

---

## 2. Process Worker Architecture (`station_process_worker`)

When invoked by `multiprocessing.Process`:
```python
def station_process_worker(station_id: int, walsh_code: np.ndarray, payload: Any, pipe_conn):
    pid = os.getpid()
    station = Station(station_id, walsh_code, name=f"Station_{station_id} (PID {pid})")
    station.load_payload(payload)
    ...
```

### Protocol States & Message Handling:
1. **`READY`**: Handshakes with the Channel hub, sending its assigned `station_id` and unique OS `pid`.
2. **`REQUEST_CHIPS`**: Pops the next bit from queue, converts to bipolar symbol $d_i \in \{+1, -1, 0\}$, multiplies by $W_i$, and sends chip vector back through the pipe.
3. **`BROADCAST_COMPOSITE`**: Receives composite channel vector $C$, computes inner product $Y_i = C \cdot W_i$, normalizes $\hat{d}_i = Y_i / N$, thresholds to recover bit $\hat{b}_i$, updates ASCII character reassembly buffer, and sends decoded confirmation.
4. **`TERMINATE`**: Verifies 100% reconstruction accuracy, sends report, and exits process cleanly.

---

## 3. Detailed Unit Operations

### 3.1 The Sender Unit (`Sender`)
- **ASCII Serialization**: Converts character strings to 8-bit MSB-first streams.
- **Bipolar NRZ Mapping**:
  $$\text{Bit 1} \implies +1, \quad \text{Bit 0} \implies -1, \quad \text{Idle} \implies 0$$
- **Spreading**: $s_i[k] = d_i \cdot W_i[k]$.

### 3.2 The Receiver Unit (`Receiver`)
- **Correlator**: Computes $Y_i = C \cdot W_i = \sum_{k=0}^{N-1} C[k] W_i[k]$.
- **Normalizer**: $\hat{d}_i = Y_i / N$.
- **Slicer Decision**:
  $$\hat{b}_i = \begin{cases} 1, & \hat{d}_i > 0.5 \\ 0, & \hat{d}_i < -0.5 \\ \text{None}, & |\hat{d}_i| \le 0.5 \end{cases}$$
- **Byte Reassembly**: Reconstructs ASCII characters from 8-bit blocks.
