# 🧪 Comprehensive Testing Guide & Verification Suite — Assignment 4: Multi-Process CDMA with Walsh Code

> **Course**: CSE/PC/B/S/314 Computer Networks Lab  
> **Topic**: Multi-Process CDMA with Walsh Codes Verification & Automated Testing  
> **Mandate**: *$k$ stations sharing the channel must be executed as $k$ independent OS processes.*  

---

## 1. Project File Structure & Test Layout

```
Assignment_4/
├── codes.py              ← Root master CLI entrypoint & interactive menu
├── simulation.py         ← Root runner for MultiProcessCDMASimulation
├── channel.py            ← Root runner for channel model & socket server
├── station.py            ← Root runner for Station, Sender, Receiver, & socket client
├── walsh.py              ← Root runner for Walsh code generator
├── dashboard.py          ← Root runner for Rich live terminal UI
├── benchmark.py          ← Root runner for scalability & SNR benchmarks
├── plot_results.py       ← Root runner for 8 publication plots generator
├── results.csv           ← Generated scalability benchmark dataset
├── benchmark_snr.csv     ← Generated SNR sweep dataset
│
├── Codes/
│   ├── codes.py          ← Master application implementation
│   ├── walsh.py          ← Walsh-Hadamard code generation & orthogonality
│   ├── channel.py        ← Linear superposition channel & standalone TCP server
│   ├── station.py        ← Station, Sender, Receiver & station_process_worker
│   ├── simulation.py     ← MultiProcessCDMASimulation (spawns k OS processes)
│   ├── dashboard.py      ← Rich live terminal dashboard UI with PIDs
│   ├── benchmark.py      ← Benchmarking engine (scalability + SNR)
│   ├── plot_results.py   ← Matplotlib publication plots engine
│   └── test_cdma.py      ← Full automated unit & multi-process test suite (20 tests)
│
├── Plots/                ← Generated publication figures (8 PNGs)
├── Theories/             ← Comprehensive theoretical documentation (11 detailed files)
└── TESTS.md              ← Quick-reference test manual at workspace root
```

---

## 2. Running Automated Tests

Run the full automated test suite executing **20 unit and multi-process integration tests**:

```bash
python3 Codes/test_cdma.py
# Or via master CLI launcher:
python3 codes.py --test
```

### Complete Test Case Matrix (20 Tests)

| Test ID | Test Function Name | Tested Module | Purpose & Validation Condition | Result |
|---|---|---|---|---|
| **TC01** | `test_next_power_of_two` | `walsh.py` | Validates rounding to powers of two ($n=1\to 2, 3\to 4, 5\to 8, 17\to 32$) | **PASS** |
| **TC02** | `test_hadamard_dimensions_and_entries` | `walsh.py` | Confirms shape $(N, N)$ and entries $\in \{+1, -1\}$ for $N \in \{2, 4, 8, 16, 32\}$ | **PASS** |
| **TC03** | `test_hadamard_symmetry` | `walsh.py` | Verifies matrix symmetry: $H = H^T$ | **PASS** |
| **TC04** | `test_hadamard_orthogonality` | `walsh.py` | Verifies Gramian matrix: $H \cdot H^T = N \cdot I_N$ (zero cross-correlation) | **PASS** |
| **TC05** | `test_invalid_dimensions` | `walsh.py` | Confirms `ValueError` on non-powers of 2 ($N=0, 3, 10$) | **PASS** |
| **TC06** | `test_linear_superposition` | `channel.py` | Confirms vector sum: $[1,1,1,1] + [1,-1,1,-1] = [2,0,2,0]$ | **PASS** |
| **TC07** | `test_idle_channel` | `channel.py` | Confirms zero vector on empty transmission | **PASS** |
| **TC08** | `test_channel_telemetry` | `channel.py` | Verifies slot counters, chip counters, and history buffers | **PASS** |
| **TC09** | `test_sender_bipolar_encoding` | `station.py` | Confirms $1 \to +1 \cdot W$, $0 \to -1 \cdot W$, $\text{None} \to 0$ | **PASS** |
| **TC10** | `test_receiver_matched_filtering` | `station.py` | Confirms $+1.0$ slicer to Bit 1, $-1.0$ slicer to Bit 0, $0.0$ to None | **PASS** |
| **TC11** | `test_text_serialization_and_reconstruction` | `station.py` | Encodes `"TEST"`, deserializes 32 bits, verifies 100% text match | **PASS** |
| **TC12** | `test_two_station_concurrent_bits` | `simulation.py` | 2 stations transmit $[1, 0, 1]$ and $[0, 1, 1]$ simultaneously; BER = 0.0 | **PASS** |
| **TC13** | `test_four_station_text_transmission` | `simulation.py` | 4 stations send distinct strings (`"NET4"`, `"CDMA"`, `"SYNC"`, `"WALS"`); 100% match | **PASS** |
| **TC14** | `test_eight_station_concurrent_data` | `simulation.py` | 8 stations send text payloads simultaneously; BER = 0.0000 | **PASS** |
| **TC15** | `test_silent_stations_isolation` | `simulation.py` | 3 stations transmit data while Station 2 is silent; Station 2 receives all None without interference | **PASS** |
| **TC16** | `test_odd_station_counts` | `simulation.py` | 3 stations allocated $N=4$ Walsh codes; executes without error | **PASS** |
| **TC17** | `test_high_snr_awgn_accuracy` | `simulation.py` | 4 stations transmit over $+25 \text{ dB}$ AWGN channel; zero bit errors | **PASS** |
| **TC18** | `test_multiprocess_pid_isolation` | `simulation.py` | **Spawns $k=4$ independent OS processes. Verifies distinct PIDs for all stations and main orchestrator.** | **PASS** |
| **TC19** | `test_multiprocess_text_reconstruction` | `simulation.py` | **4 concurrent OS processes transmit distinct text messages over IPC pipes with 100% perfect reconstruction.** | **PASS** |
| **TC20** | `test_multiprocess_eight_stations` | `simulation.py` | **8 concurrent OS processes run simultaneously with distinct PIDs; verifies zero bit errors across all processes.** | **PASS** |

### Test Execution Log:
```
Ran 20 tests in 0.713s

OK
```

---

## 3. Running Multi-Terminal Sockets Mode

To run each station from independent terminal windows:

### Terminal 1: Start Channel Server
```bash
python3 channel.py --serve --port 9000 --stations 4 --slots 32
```

### Terminals 2 to 5: Connect Station Processes
```bash
# Terminal 2:
python3 station.py --connect --id 0 --port 9000 --msg "NET4"

# Terminal 3:
python3 station.py --connect --id 1 --port 9000 --msg "CDMA"

# Terminal 4:
python3 station.py --connect --id 2 --port 9000 --msg "SYNC"

# Terminal 5:
python3 station.py --connect --id 3 --port 9000 --msg "WALS"
```

The Channel server and the 4 station processes will handshake, exchange Walsh codes, perform synchronous slot transmissions, and print 100% perfect reconstruction!
