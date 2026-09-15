# 🧪 Testing Guide — Assignment 3: CSMA Techniques with Collision Detection

> Complete instructions for running, testing, and verifying all modules and protocols.

---

## 📁 Project File Structure

```
Assignment_3/
├── channel.py            ← Shared channel model (IDLE/BUSY/COLLISION state machine)
├── station.py            ← Station class with BEB backoff & metrics
├── csma_protocols.py     ← All 4 CSMA protocol implementations
├── simulation.py         ← Discrete-event simulation engine (main entry point)
├── dashboard.py          ← Rich live terminal dashboard (scope extra)
├── benchmark.py          ← Automated sweep runner → results.csv
├── plot_results.py       ← Matplotlib graph generator → plots/
├── results.csv           ← Auto-generated benchmark data
├── plots/                ← Generated PNG plots directory
│
└── Theories/
    ├── theories.md              ← General theory document
    ├── channel_theory.md        ← Theory for channel.py
    ├── station_theory.md        ← Theory for station.py
    ├── csma_protocols_theory.md ← Theory for csma_protocols.py
    ├── simulation_theory.md     ← Theory for simulation.py
    ├── dashboard_theory.md      ← Theory for dashboard.py
    ├── benchmark_theory.md      ← Theory for benchmark.py
    ├── plot_results_theory.md   ← Theory for plot_results.py
    └── gtest.md                 ← This file — test cases & verification
```

---

## ✅ Prerequisites

- **Python 3.10+** (required for `X | Y` type union syntax)
- **No external libraries** needed for core simulation (only Python standard library)
- **Optional**: `rich` (for dashboard), `matplotlib pandas numpy` (for plotting)

```bash
python3 --version     # Must be 3.10+

# Optional installs
pip3 install rich                      # For dashboard
pip3 install matplotlib pandas numpy   # For plotting
```

---

## 🔬 Step 1 — Test Individual Modules

Each module has a built-in `__main__` self-test. Run them **in dependency order**:

### 1a. Channel Module
```bash
cd Assignment_3
python3 channel.py
```

**Expected output:**
```
============================================================
  Channel Module — Self-Test
============================================================
[1] Channel initializes to IDLE            ✓
[2] Single transmitter → BUSY              ✓
[3] Two transmitters → COLLISION            ✓
[4] Abort returns collided IDs              ✓
[5] Channel IDLE after abort                ✓
[6] Jam signal recorded                     ✓
[7] Auto-cleanup after frame duration       ✓
[8] Reset clears all state                  ✓
[9] Slot recording (idle/busy/collision)    ✓

All channel self-tests passed ✅
============================================================
```

**What to check:**
- All 9 tests show `✓`
- State transitions: IDLE → BUSY → COLLISION → IDLE work correctly
- `abort_all_transmissions` returns the correct set of station IDs
- Auto-cleanup removes stations after their frame duration expires

---

### 1b. Station Module
```bash
python3 station.py
```

**Expected output:**
```
============================================================
  Station Module — Self-Test
============================================================
[1] Station initializes (IDLE, 5 frames)   ✓
[2] Start transmission → TRANSMITTING      ✓
[3] Successful completion → IDLE, 4 left    ✓
[4] Collision → WAITING, backoff=N slots    ✓
[5] BEB escalation (k=5 after 5 collisions) ✓
[6] Max retries exceeded → frame dropped     ✓
[7] Backoff timer ticks down → IDLE          ✓
[8] Last frame sent → DONE                  ✓
[9] Avg delay = 12.5                        ✓

All station self-tests passed ✅
============================================================
```

**What to check:**
- Station state transitions follow: IDLE → TRANSMITTING → (IDLE or WAITING or DONE)
- BEB escalation: backoff_k increments with each collision
- After max_retries (3 in test), frame is dropped and `dropped_frames` increments
- Backoff timer correctly ticks down to 0, transitioning WAITING → IDLE
- Average delay calculation is correct

---

### 1c. CSMA Protocols Module
```bash
python3 csma_protocols.py
```

**Expected output:**
```
============================================================
  CSMA Protocols Module — Self-Test
============================================================
[1] Non-Persistent: IDLE → TRANSMIT         ✓
[2] Non-Persistent: BUSY → SENSE_BUSY+WAIT  ✓
[3] 1-Persistent: IDLE → TRANSMIT            ✓
[4] 1-Persistent: BUSY → stays IDLE (sense) ✓
[5] p-Persistent: IDLE, r<p → TRANSMIT      ✓
[6] p-Persistent: IDLE, r≥p → DEFER         ✓
[7] CSMA/CD: IDLE → TRANSMIT                ✓
[8] Protocol dispatcher works               ✓
[9] p=1.0 matches 1-persistent behavior     ✓

All CSMA protocol self-tests passed ✅
============================================================
```

**What to check:**
- Each protocol makes the correct decision given channel state
- Non-Persistent: BUSY → station enters WAITING (random delay)
- 1-Persistent: BUSY → station stays IDLE (will re-sense next slot)
- p-Persistent: random < p → TRANSMIT; random ≥ p → DEFER
- p=1.0 degenerates to 1-Persistent behavior
- Protocol dispatcher correctly maps names to functions

---

### 1d. Dashboard Module
```bash
python3 dashboard.py
```

**Expected output:**
```
============================================================
  Dashboard Module — Self-Test
============================================================
[1] NullDashboard operates silently         ✓
[2] Sparkline: ▁▃▅▆█▇▅▃▂▁                  ✓
[3] Rich library is available               ✓
[4] Dashboard instantiation                 ✓

All dashboard self-tests passed ✅
============================================================
```

**What to check:**
- NullDashboard doesn't crash when called with any arguments
- Sparkline rendering produces characters from `▁▂▃▄▅▆▇█`
- Rich import succeeds (or shows warning if not installed)

---

## 🚀 Step 2 — Run Single Simulation

### 2a. All Protocols Comparison (Quick Test)
```bash
python3 simulation.py --protocol all --stations 5 --sim-time 500
```

**Expected output (format):**
```
╔════════════════════════════════════════════════════════════╗
║         CSMA Protocol Simulator — Assignment 3           ║
╠════════════════════════════════════════════════════════════╣
║  Stations (N)     : 5                                    ║
║  Simulation slots : 500                                  ║
...
╚════════════════════════════════════════════════════════════╝

Running all four protocols...

──────────────────────────────────────────────────────────────────────────────────
Protocol               N     p  Collisions  Frames  Dropped  AvgDelay   Throughput   Util%   Coll%
──────────────────────────────────────────────────────────────────────────────────
Non-Persistent CSMA    5  0.30         ...     ...      ...       ...       ...      ...     ...
1-Persistent CSMA      5  0.30         ...     ...      ...       ...       ...      ...     ...
p-Persistent CSMA      5  0.30         ...     ...      ...       ...       ...      ...     ...
CSMA/CD                5  0.30         ...     ...      ...       ...       ...      ...     ...
──────────────────────────────────────────────────────────────────────────────────

📊 Observations:
   Best throughput  : CSMA/CD (...)
   Least collisions : Non-Persistent CSMA (...)
```

**What to verify:**
- All 4 protocols produce results
- CSMA/CD should generally have best throughput
- Non-Persistent should have fewest collisions
- No errors or exceptions

---

### 2b. Single Protocol with Verbose Output
```bash
python3 simulation.py --protocol csma_cd --stations 3 --sim-time 100 --verbose
```

**What to verify:**
- Per-slot events are printed (TRANSMIT, SENSE_BUSY, COLLISION)
- Collisions trigger abort + BEB backoff
- Frames get successfully delivered

---

### 2c. Reproducibility with Seed
```bash
python3 simulation.py --protocol p_persistent --stations 5 --sim-time 200 --seed 42
python3 simulation.py --protocol p_persistent --stations 5 --sim-time 200 --seed 42
```

**What to verify:**
- Both runs produce **identical** results (same collisions, frames, delay, throughput)

---

## 🧪 Step 3 — Correctness Tests

### Test 3a: Single Station = Zero Collisions
```bash
python3 simulation.py --protocol all --stations 1 --sim-time 1000
```

**Expected:**
| Protocol | Collisions | Expected |
|----------|:----------:|:--------:|
| Non-Persistent | 0 | ✓ |
| 1-Persistent | 0 | ✓ |
| p-Persistent | 0 | ✓ |
| CSMA/CD | 0 | ✓ |

**Rationale**: With only one station, there's nobody to collide with. All protocols should deliver all frames without any collisions.

---

### Test 3b: Two Stations — Some Collisions
```bash
python3 simulation.py --protocol all --stations 2 --sim-time 1000
```

**Expected:**
- Collisions > 0 for most protocols (especially 1-Persistent)
- Non-Persistent should have the fewest collisions
- All frames should eventually be delivered (dropped = 0 or very small)

---

### Test 3c: Many Stations — High Collision Rate
```bash
python3 simulation.py --protocol all --stations 20 --sim-time 2000
```

**Expected:**
- Significantly more collisions than N=2
- 1-Persistent should have the MOST collisions
- CSMA/CD should have best throughput despite collisions (fast recovery)
- Some frames may be dropped at very high contention

---

### Test 3d: Monotonicity — Collisions Increase with N
```bash
for N in 2 5 10 15 20; do
    echo "=== N=$N ==="
    python3 simulation.py --protocol csma_cd --stations $N --sim-time 500 --seed 42
done
```

**Expected:** Collision count increases monotonically with N.

---

### Test 3e: p=1.0 Matches 1-Persistent
```bash
python3 simulation.py --protocol p_persistent --stations 5 --p-value 1.0 --sim-time 500 --seed 42
python3 simulation.py --protocol 1_persistent --stations 5 --sim-time 500 --seed 42
```

**Expected:** Results should be very similar (not identical due to implementation details, but same order of magnitude for all metrics).

---

### Test 3f: p=0.01 — Very Low Collision, High Delay
```bash
python3 simulation.py --protocol p_persistent --stations 5 --p-value 0.01 --sim-time 2000
```

**Expected:**
- Very few collisions (near 0)
- Very high average delay (stations rarely decide to transmit)
- Low throughput (channel is mostly idle even when stations have data)

---

## 📊 Step 4 — Benchmark Sweep

### 4a. Full Benchmark Run
```bash
python3 benchmark.py
```

**Expected:**
- Progress bars showing p-sweep (60 runs) and N-sweep (180 runs)
- Total: 240 simulations
- Generates `results.csv`
- Completes in ~30-120 seconds depending on hardware

**What to verify:**
```bash
wc -l results.csv        # Should be 241 lines (1 header + 240 data)
head -5 results.csv       # Check CSV format is correct
```

---

### 4b. Quick Benchmark (Faster)
```bash
python3 benchmark.py --runs 2 --sim-time 300 --frames 30
```

**Expected:** Faster completion (~10-30s), fewer data points but same format.

---

## 📈 Step 5 — Generate Plots

### 5a. Generate All Figures
```bash
python3 plot_results.py --no-show
```

**Expected output:**
```
╔════════════════════════════════════════════════════════════╗
║         CSMA Plot Generator — Assignment 3               ║
╚════════════════════════════════════════════════════════════╝

  Loaded 241 rows from results.csv

  Generating figures...
  ──────────────────────────────────────────────────────
  Saved: plots/fig1_p_collisions.png
  Saved: plots/fig2_p_delay.png
  Saved: plots/fig3_p_throughput.png
  Saved: plots/fig4_n_collisions.png
  Saved: plots/fig5_n_delay.png
  Saved: plots/fig6_n_throughput.png
  Saved: plots/fig7_combined_summary.png
  Saved: plots/fig8_theoretical_throughput.png
  Saved: plots/fig9_p_heatmap.png
  ──────────────────────────────────────────────────────

  ✅ All figures saved to .../plots/
```

**What to verify:**
```bash
ls plots/       # Should contain 9 PNG files
```

### 5b. Verify Plot Content

| Figure | What to look for |
|--------|-----------------|
| fig1 | Collisions increase with p (especially p > 0.5) |
| fig2 | Delay decreases then increases (U-shape or decreasing) as p grows |
| fig3 | Throughput peaks at intermediate p (around 0.2-0.3 for N=5) |
| fig4 | All curves rise with N; 1-Persistent rises fastest |
| fig5 | All curves rise with N |
| fig6 | All curves decline with N; CSMA/CD declines slowest |
| fig7 | Combined 2×3 panel matches individual figures |
| fig8 | Theoretical curves match textbook shapes |
| fig9 | Heatmap shows bright band at intermediate p |

---

## 🎨 Step 6 — Dashboard Demo

### 6a. Live Dashboard
```bash
python3 simulation.py --protocol csma_cd --stations 8 --sim-time 500 --dashboard
```

**What to verify:**
- Rich terminal UI appears with:
  - Channel state indicator (cycling through IDLE/BUSY/COLLISION)
  - Station grid showing 8 stations with color-coded states
  - Live metrics updating
  - Sparkline charts showing trends
  - Scrolling event log
  - Progress bar advancing to 100%

### 6b. Dashboard Fallback (Without Rich)
```bash
pip3 uninstall rich   # temporarily remove
python3 simulation.py --protocol csma_cd --stations 5 --dashboard
```

**Expected:** Warning message about Rich not being installed, then normal text output.

---

## 🔧 Step 7 — Edge Cases

### 7a. Zero Frames
```bash
python3 simulation.py --protocol csma_cd --stations 5 --frames 0
```
**Expected:** Simulation completes immediately (all stations in DONE state).

### 7b. One Station, One Frame
```bash
python3 simulation.py --protocol all --stations 1 --frames 1 --sim-time 100
```
**Expected:** 0 collisions, 1 frame sent, throughput > 0.

### 7c. Very Short Simulation
```bash
python3 simulation.py --protocol all --stations 10 --sim-time 5
```
**Expected:** Runs without errors. Very few or zero frames delivered.

### 7d. High Contention Stress Test
```bash
python3 simulation.py --protocol all --stations 50 --sim-time 5000 --frames 10
```
**Expected:** Many collisions, some dropped frames. CSMA/CD should still deliver the most frames.

---

## ✅ Complete Test Checklist

| # | Test | Command | Expected |
|---|------|---------|----------|
| 1 | Channel self-test | `python3 channel.py` | 9/9 pass |
| 2 | Station self-test | `python3 station.py` | 9/9 pass |
| 3 | Protocols self-test | `python3 csma_protocols.py` | 9/9 pass |
| 4 | Dashboard self-test | `python3 dashboard.py` | 4/4 pass |
| 5 | All protocols comparison | `simulation.py --protocol all -N 5` | Table with 4 rows |
| 6 | Verbose single run | `simulation.py --protocol csma_cd -N 3 -v` | Per-slot events |
| 7 | Reproducibility (seed) | Two runs with `--seed 42` | Identical results |
| 8 | N=1 → 0 collisions | `simulation.py --protocol all -N 1` | All collisions = 0 |
| 9 | N=2 → some collisions | `simulation.py --protocol all -N 2` | collisions > 0 |
| 10 | N=20 → many collisions | `simulation.py --protocol all -N 20` | High collisions |
| 11 | Monotonicity | Loop N=2,5,10,15,20 | Collisions ↑ with N |
| 12 | p=1.0 ≈ 1-persistent | Compare both | Similar results |
| 13 | p=0.01 → low collision | `--p-value 0.01` | Near-zero collisions |
| 14 | Benchmark sweep | `python3 benchmark.py` | 240 runs in CSV |
| 15 | Plot generation | `python3 plot_results.py` | 9 PNGs in plots/ |
| 16 | Dashboard demo | `--dashboard` flag | Live UI renders |
| 17 | Edge: 0 frames | `--frames 0` | Immediate completion |
| 18 | Edge: 50 stations | `-N 50 --sim-time 5000` | No crash |

---

## 🚨 Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: channel` | Running from wrong directory | `cd Assignment_3` first |
| `TypeError: unsupported operand type(s)` | Python < 3.10 | Upgrade to Python 3.10+ |
| `ImportError: rich` | Rich not installed | `pip3 install rich` |
| `ImportError: matplotlib` | Matplotlib not installed | `pip3 install matplotlib pandas numpy` |
| `No p-sweep data found` | Empty results.csv | Run `python3 benchmark.py` first |
| Dashboard not rendering | Terminal too small | Resize terminal to ≥120×40 |
| Simulation takes too long | Too many stations or slots | Reduce `--sim-time` or `--stations` |
