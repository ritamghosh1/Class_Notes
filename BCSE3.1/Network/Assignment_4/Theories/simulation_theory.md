# Simulation Module Theory — `simulation.py`

> **File**: `simulation.py`  
> **Classes**: `MultiProcessCDMASimulation`, `CDMASimulation`  
> **Role**: Multi-process and discrete-time simulation coordinator  
> **Architecture**: Spawns $k$ independent OS worker processes for $k$ stations  

---

## 1. What This Module Does

`simulation.py` coordinates the multi-station CDMA network session. Conforming to the architectural requirement that $k$ stations sharing the channel must run as $k$ independent processes, this module provides:
- **`MultiProcessCDMASimulation`**: The primary coordinator. It spawns $k$ distinct OS child processes using `multiprocessing.Process`, sets up duplex IPC pipes, synchronizes slotted transmissions, collects per-process telemetry, and manages process shutdown.
- **`CDMASimulation`**: A fast, in-memory reference coordinator used for high-volume statistical Monte Carlo sweeps (e.g. 10,000+ bits).

---

## 2. Multi-Process Lifecycle & Synchronization

```
Master Orchestrator Process (PID M)
  │
  ├─► mp.Pipe(duplex=True) for i in 0..k-1
  │
  ├─► mp.Process(target=station_process_worker, args=(i, W_i, payload, pipe))
  │   ├── Spawn Child Process 0 (PID P0)
  │   ├── Spawn Child Process 1 (PID P1)
  │   └── Spawn Child Process k-1 (PID Pk-1)
  │
  ├─► Handshake:
  │   Child processes reply with {"type": "READY", "pid": P_i}
  │   Orchestrator maps PIDs to stations
  │
  ├─► Synchronous Slotted Loop (t = 0 .. total_slots - 1):
  │   1. Orchestrator sends {"type": "REQUEST_CHIPS"} to all k pipes
  │   2. Each child process produces chips s_i and replies with {"type": "CHIPS"}
  │   3. Channel computes linear superposition C = sum(s_i) + AWGN(SNR)
  │   4. Orchestrator broadcasts {"type": "BROADCAST_COMPOSITE", "composite": C}
  │   5. Each child process correlates C · W_i, decodes bit, and replies with {"type": "DECODED"}
  │   6. Telemetry (including all child PIDs) is packaged for the Dashboard / Log
  │
  └─► Termination & Cleanup:
      1. Orchestrator sends {"type": "TERMINATE"} to all k child processes
      2. Each child process sends final verification report {"type": "REPORT"}
      3. Orchestrator closes pipes and calls proc.join() on all child processes
```

---

## 3. Concurrency and Process Isolation Guarantees

1. **Virtual Address Space Decoupling**: Each station process executes in its own isolated memory space. Station $i$ cannot inspect or alter Station $j$'s transmission queue or demodulation buffer.
2. **True Operating System Concurrency**: On multi-core systems, the OS kernel schedules the $k$ station processes across distinct CPU cores simultaneously, reflecting authentic distributed radio node behavior.
3. **No GIL Contention**: Because each station is an independent OS process with its own Python interpreter instance, CPU-bound operations execute without Python Global Interpreter Lock (GIL) contention.
4. **Resilient Error Trapping**: Unhandled errors in one child process do not corrupt the orchestrator or adjacent station processes.
