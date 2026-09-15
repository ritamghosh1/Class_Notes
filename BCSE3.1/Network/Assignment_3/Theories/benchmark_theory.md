# Benchmark Module Theory — `benchmark.py`

> **File**: `benchmark.py`  
> **Role**: Automated parameter sweep runner  
> **Layer**: Experiment / Data collection

---

## 1. What This Module Does

`benchmark.py` automates the process of running the simulation across many configurations and collecting results into a CSV file. This CSV is then consumed by `plot_results.py` to generate all required graphs.

---

## 2. Experimental Methodology

### Why Sweep?

The assignment asks us to analyze **how parameters affect performance**:
1. How does **p** affect p-persistent CSMA? (fixed N)
2. How does **N** affect all four protocols?

A single simulation run has randomness (BEB, p-persistent coin flips). To get reliable results, we **average over multiple runs** (default: 5 runs per configuration).

### Sweep Design

#### Sweep 1: p-Persistent (p varies, N fixed)

| Parameter | Values |
|-----------|--------|
| Protocol | p-persistent only |
| N (fixed) | 5 |
| p (varied) | 0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0 |
| Runs per config | 5 |
| **Total simulations** | 12 × 5 = **60** |

#### Sweep 2: All Protocols (N varies)

| Parameter | Values |
|-----------|--------|
| Protocols | Non-Persistent, 1-Persistent, p-Persistent, CSMA/CD |
| N (varied) | 2, 3, 4, 5, 6, 8, 10, 15, 20 |
| p (for p-persistent) | 1/N (optimal) |
| Runs per config | 5 |
| **Total simulations** | 9 × 4 × 5 = **180** |

**Grand total**: 60 + 180 = **240 simulations**

---

## 3. CSV Output Format

Each row in `results.csv` contains:

```csv
sweep_type,protocol,N,p,run,collisions,frames_sent,attempts,dropped,avg_delay,throughput,utilization,collision_rate
p_sweep,p_persistent,5,0.1,0,12,487,499,1,23.4521,0.487,0.3214,0.0123
p_sweep,p_persistent,5,0.1,1,15,481,496,2,24.1234,0.481,0.3189,0.0156
...
```

### Key Columns

| Column | Meaning |
|--------|---------|
| `sweep_type` | `p_sweep` or `n_sweep` (for filtering in plots) |
| `protocol` | Protocol name string |
| `N` | Number of stations |
| `p` | Persistence probability used |
| `run` | Run number (0 to runs-1) |
| `collisions` | Total collision events |
| `avg_delay` | Average per-frame delay |
| `throughput` | Frames delivered per slot |
| `utilization` | Channel utilization fraction |

---

## 4. Progress Tracking

The benchmark displays a real-time progress bar with ETA:

```
  p-sweep: [████████████████░░░░░░░░░░░░░░░░░░░░░░░░]  41.7%  ETA:  12.3s
```

This uses a simple calculation:
- `fraction = completed_runs / total_runs`
- `ETA = (elapsed / fraction) - elapsed`

---

## 5. Usage

```bash
# Default settings
python3 benchmark.py

# Custom output and more runs
python3 benchmark.py --output my_results.csv --runs 10

# Faster sweep with shorter simulations
python3 benchmark.py --sim-time 500 --frames 50

# Then plot
python3 plot_results.py --csv results.csv
```
