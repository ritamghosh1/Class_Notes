# Dashboard Module Theory — `dashboard.py`

> **File**: `dashboard.py`  
> **Class**: `CDMADashboard`  
> **Role**: Terminal user interface, real-time multi-process visualization & telemetry  
> **Library**: `rich`  

---

## 1. What This Module Does

`dashboard.py` renders a live terminal dashboard displaying the execution of the multi-process CDMA network. It visually tracks:
- **OS Process IDs (PIDs)**: Explicitly identifies the independent operating system process running each station.
- **Assigned Walsh Codes**: Shows codewords $W_i$ and verified mutual orthogonality.
- **Channel Superposition Waveform**: Live ASCII/Unicode chip voltage bars (`▲+3`, `▼-1`, `─ 0`) and energy sparklines.
- **Process Transmission Matrix**: Per-process transmission bits, bipolar values, spread chips, dot products, decoded bits, match status, and reconstructed text.
- **Multi-Process Event Log**: Real-time timestamps of process handshakes, synchronization events, and completion reports.

---

## 2. Multi-Process Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ⚡ MULTI-PROCESS CDMA WITH WALSH CODES ⚡                                   │
│ Architecture: True Multi-Process (k=4 OS Processes)                         │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ Walsh Code & Process Allocation      │ Shared Channel Superposition Waveform│
│ Station 0 [PID 93195]: [+1,+1,+1,+1] │ Composite: [ +3, -1, -1, -1 ]        │
│ Station 1 [PID 93196]: [+1,-1,+1,-1] │ Waveform:  ▲+3  ▼-1  ▼-1  ▼-1        │
│ Station 2 [PID 93197]: [+1,+1,-1,-1] │ Energy: 12.00 | Sparkline: ████████  │
│ Station 3 [PID 93198]: [+1,-1,-1,+1] │                                      │
├──────────────────────────────────────┴──────────────────────────────────────┤
│ Multi-Process Spreading & Correlator Despreading Matrix                     │
│ Node   │ OS PID │ Bit TX │ Bipolar │ Spread Chips │ Dot Prod │ Bit RX │Match│
│ St 0   │ 93195  │   1    │   +1    │ [+1,+1,+1,+1]│   +4.0   │   1    │✓ OK │
│ St 1   │ 93196  │   0    │   -1    │ [-1,+1,-1,+1]│   -4.0   │   0    │✓ OK │
│ St 2   │ 93197  │   1    │   +1    │ [+1,+1,-1,-1]│   +4.0   │   1    │✓ OK │
│ St 3   │ 93198  │   0    │   -1    │ [-1,+1,+1,-1]│   -4.0   │   0    │✓ OK │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ Network Telemetry & Metrics          │ Multi-Process Event Log              │
│ Total Bits: 128 | Chips: 128         │ [15:47:15] [PROC] St 0 on PID 93195  │
│ Bit Errors: 0 | BER: 0.0000          │ [15:47:16] [DEBUG] Slot 28 Decoded   │
│ Processing Gain: 6.02 dB             │ [15:47:17] [SUCCESS] All Joined      │
└──────────────────────────────────────┴──────────────────────────────────────┘
```
