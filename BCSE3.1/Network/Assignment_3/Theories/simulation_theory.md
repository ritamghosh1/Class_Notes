# Simulation Engine Theory — `simulation.py`

> **File**: `simulation.py`  
> **Role**: Discrete-event simulation engine & main entry point  
> **Layer**: Orchestration

---

## 1. What This Module Does

`simulation.py` is the **heart** of the project. It runs the discrete-event simulation loop that models time advancing slot-by-slot, coordinates all stations' protocol decisions, detects and resolves collisions, tracks completed transmissions, and collects performance metrics.

It also provides the CLI entry point for running simulations.

---

## 2. Discrete-Event Simulation (DES)

### What is DES?

Unlike continuous simulation, DES advances time in **discrete steps** (slots). At each step, the system:
1. Processes all events scheduled for this time step
2. Generates new events based on current state
3. Advances to the next step

### Our Slot-Based Approach

```
t=0        t=1        t=2        t=3        t=4
 │          │          │          │          │
 ▼          ▼          ▼          ▼          ▼
┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐
│Tick  │  │Tick  │  │Tick  │  │Tick  │  │Tick  │
│timers│  │timers│  │timers│  │timers│  │timers│
│      │  │      │  │      │  │      │  │      │
│Decide│  │Decide│  │Decide│  │Decide│  │Decide│
│      │  │      │  │      │  │      │  │      │
│Check │  │Check │  │Check │  │Check │  │Check │
│collis│  │collis│  │collis│  │collis│  │collis│
│      │  │      │  │      │  │      │  │      │
│Check │  │Check │  │Check │  │Check │  │Check │
│done  │  │done  │  │done  │  │done  │  │done  │
└──────┘  └──────┘  └──────┘  └──────┘  └──────┘
```

Each slot executes **6 phases** in strict order:

| Phase | Action | Why this order? |
|-------|--------|----------------|
| 1 | Tick backoff timers | Stations finishing backoff become IDLE before deciding |
| 2 | Protocol decisions | All IDLE stations with data execute their protocol |
| 3 | Collision check | After all decisions, check if 2+ stations started tx |
| 4 | Handle collisions | Abort collided tx, send jam (CSMA/CD), BEB for all |
| 5 | Check completions | Stations whose frame_duration has elapsed → success |
| 6 | Record slot stats | Track channel state for utilization/collision metrics |

### Why This Order Matters

- Timers tick **before** decisions so freshly-unblocked stations can act this slot
- Collision check happens **after all decisions** so simultaneous starts are caught
- Completions check **after collisions** so collided frames aren't marked successful

---

## 3. Simulation Parameters (`SimConfig`)

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `num_stations` | 5 | Number of contending stations N |
| `simulation_slots` | 1000 | Total simulation duration (slots) |
| `slot_time` | 1.0 | Duration of one slot |
| `frame_duration` | 10.0 | How long a frame occupies the channel |
| `propagation_delay` | 2.0 | One-way signal propagation time |
| `jam_duration` | 4.0 | Duration of jam signal (CSMA/CD) |
| `frames_per_station` | 100 | Frames each station must send |
| `p_value` | 0.3 | Persistence probability |
| `max_retries` | 16 | BEB max retries before drop |

---

## 4. Metrics Collection (`SimulationResult`)

After simulation completes, we compute:

| Metric | Formula |
|--------|---------|
| **Collisions** | Total collision events detected by the channel |
| **Frames sent** | Sum of `frames_sent` across all stations |
| **Avg delay** | Total delay / frames_sent |
| **Throughput** | frames_sent / total_slots |
| **Utilization** | busy_slots / total_slots |
| **Collision rate** | collision_slots / total_slots |

---

## 5. Multi-Protocol Comparison

`run_all_protocols()` runs all four protocols with identical parameters and returns a list of `SimulationResult`. The `print_results_table()` function formats this into a comparison table for quick analysis.

---

## 6. CLI Interface

```
python3 simulation.py --protocol csma_cd --stations 5 --sim-time 1000
python3 simulation.py --protocol all --stations 10 --verbose
python3 simulation.py --protocol p_persistent --stations 5 --p-value 0.3 --dashboard
```

The `--seed` flag enables reproducible runs for debugging and testing.
