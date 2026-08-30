# 🧪 Testing Guide — Assignment 2: Data Link Layer Simulation

> Complete instructions for running, testing, and verifying all modules and protocols.

---

## 📁 Project File Structure

```
Assignment_2/
├── error_detection.py   ← CRC-32 & Internet Checksum (ported from Assignment 1 C++)
├── error_injection.py   ← Bit-flip & burst error injectors (ported from Assignment 1 C++)
├── frame.py             ← Framing module: build / parse / check frames
├── channel.py           ← Channel simulation: delay, loss, bit errors over TCP
├── timer.py             ← Per-frame timers + adaptive RTT/RTO (RFC 6298 EWMA)
├── sender.py            ← Sender program: SAW / GBN / SR protocols
├── receiver.py          ← Receiver program: SAW / GBN / SR protocols
├── input.txt            ← Sample input file to transmit
└── output.txt           ← Written by receiver.py after transfer (auto-created)
```

---

## ✅ Prerequisites

- **Python 3.10+** (required for `bytes | bytearray` type union syntax)
- No external libraries needed — only Python standard library

Check your Python version:
```bash
python3 --version
```

---

## 🔬 Step 1 — Test Individual Modules

Each module has a built-in `__main__` self-test. Run them **in this order**:

### 1a. Error Detection Module
```bash
cd Assignment_2
python3 error_detection.py
```

**Expected output:**
```
[Checksum] data=b'Hello, Network!'
           checksum = 0x4B64
           verify   = True

[CRC-32]   data=b'Hello, Network!'
           crc32  = 0xAE3493FB
           verify = True
           packed = ae:34:93:fb
```

**What to check:**
- `verify = True` for both Checksum and CRC-32
- The packed FCS is 4 bytes (colon-separated hex)

---

### 1b. Error Injection Module
```bash
python3 error_injection.py
```

**Expected output:**
```
Original  : 48 65 6c 6c 6f ... 
RandomBit : 48 65 6c 6c 6f ... (bytes changed: 1)
Burst(16) : 48 65 6c 6c 6f ... (bytes changed: 3)
OddAnom   : 48 65 6c 6c 6f ... (bytes changed: 3)
```

**What to check:**
- `RandomBit` changes exactly **1** byte
- `Burst(16)` changes **2–3** bytes (16-bit burst spans byte boundaries)
- `OddAnom` changes an odd number of bytes (result of 3/5/7 bit flips)

---

### 1c. Frame Module
```bash
python3 frame.py
```

**Expected output:**
```
[1] build_frame(seq=0)
    frame size     : 65 bytes  (expected 65)

[2] parse_frame()
    mac_src  : AA:BB:CC:DD:EE:01
    mac_dst  : AA:BB:CC:DD:EE:02
    seq_no   : 0

[3] check_frame() on clean frame  -> PASS ✓
[4] check_frame() on corrupted    -> FAIL ✗ (expected)

[6] read_file_chunks(): 8 chunks  (expected 8)
[7] All frames pass integrity check: YES ✓
```

**What to check:**
- Frame size = `15 (header) + 46 (payload) + 4 (FCS)` = **65 bytes**
- Clean frame → `PASS ✓`, corrupted frame → `FAIL ✗`
- All 8 frames from the temp file pass CRC

---

### 1d. Timer Module
```bash
python3 timer.py
```

**Expected output (values vary due to random RTTs):**
```
 Seq   Sample RTT        SRTT        RTO
   0       47.2 ms      47.0 ms    236.0 ms
   1       83.5 ms      52.0 ms    208.0 ms
   ...
After 60 ms sleep — expired: True
After cancel      — expired: False
```

**What to check:**
- SRTT converges towards the average of random RTTs
- RTO = SRTT + 4 × RTTVAR (always ≥ SRTT)
- `is_expired()` returns `True` after the timeout has passed
- `cancel()` stops the timer (returns `False` afterwards)

---

### 1e. Channel Module
```bash
python3 channel.py
```

**Expected output:**
```
[SERVER] Listening on 127.0.0.1:59876 ...
[CLIENT] Connected to 127.0.0.1:59876
[HH:MM:SS] [CLIENT] DELAY — sleeping X ms
[Test] Match   : YES ✓
```

**What to check:**
- `Match: YES ✓` — data sent equals data received

---

## 🚀 Step 2 — Run the Full Sender + Receiver

Each transfer needs **two terminal windows** — one for the Receiver (start first) and one for the Sender.

### Terminal layout:
```
Terminal A (Receiver)          Terminal B (Sender)
──────────────────────         ────────────────────
python3 receiver.py ...   ←→  python3 sender.py ...
```

---

## Protocol 1: Stop-and-Wait (SAW)

### Clean channel (no errors)

**Terminal A — Receiver:**
```bash
python3 receiver.py --protocol saw --output output_saw.txt --verbose
```

**Terminal B — Sender:**
```bash
python3 sender.py --protocol saw --input input.txt --p-error 0.0 --p-loss 0.0 --delay 10 --verbose
```

**Expected Receiver output:**
```
[RECEIVER] Connection from 127.0.0.1:XXXXX
[RECEIVER][SAW] Ready. Waiting for frames ...
[HH:MM:SS] [RECEIVER] Frame seq=0 received — FCS OK
[HH:MM:SS] [RECEIVER] Accepted seq=0 → sent ACK 0
[HH:MM:SS] [RECEIVER] Frame seq=1 received — FCS OK
...
[RECEIVER] Output written to 'output_saw.txt'
```

**Expected Sender output:**
```
[SENDER][SAW] Starting transmission ...
[HH:MM:SS] [SENDER] Sent frame seq=0
[HH:MM:SS] [SENDER] ACK 0 received, RTT=XX.Xms, RTO=XXX.Xms
...
[SENDER][SAW] ---- SAW Summary ----
  Retransmissions    : 0
  Channel efficiency : 100.0%
```

---

### With bit errors (p-error = 0.2)

**Terminal A:**
```bash
python3 receiver.py --protocol saw --output output_saw_err.txt --verbose
```

**Terminal B:**
```bash
python3 sender.py --protocol saw --input input.txt --p-error 0.2 --p-loss 0.0 --delay 10 --verbose
```

**What to watch:** The receiver discards corrupted frames (prints `FCS FAIL`). The sender will print `TIMEOUT` and retransmit. Efficiency will drop below 100%.

---

### With frame loss (p-loss = 0.3)

**Terminal A:**
```bash
python3 receiver.py --protocol saw --output output_saw_loss.txt
```

**Terminal B:**
```bash
python3 sender.py --protocol saw --input input.txt --p-error 0.0 --p-loss 0.3 --delay 10 --timeout 300
```

**What to watch:** The sender prints `TIMEOUT` and retransmits dropped frames. Retransmission count will be ~30% of total frames.

---

## Protocol 2: Go-Back-N (GBN)

### Clean channel with window size 4

**Terminal A:**
```bash
python3 receiver.py --protocol gbn --output output_gbn.txt --verbose
```

**Terminal B:**
```bash
python3 sender.py --protocol gbn --window 4 --input input.txt --p-error 0.0 --p-loss 0.0 --delay 10 --verbose
```

**What to watch:** Sender sends 4 frames before waiting for ACKs. Receiver sends cumulative ACKs.

---

### With errors (p-error = 0.2)

**Terminal A:**
```bash
python3 receiver.py --protocol gbn --output output_gbn_err.txt --verbose
```

**Terminal B:**
```bash
python3 sender.py --protocol gbn --window 4 --input input.txt --p-error 0.2 --p-loss 0.0 --delay 10 --verbose
```

**What to watch:** When a frame is corrupted, the receiver discards it and all subsequent out-of-order frames. The sender retransmits the **entire window** on timeout. Retransmissions >> SAW at the same error rate.

---

### Varying window sizes

Try `--window 1`, `--window 4`, `--window 8` and compare efficiency:
```bash
# Window = 1 (equivalent to SAW)
python3 sender.py --protocol gbn --window 1 --input input.txt --p-error 0.0 --p-loss 0.0 --delay 10

# Window = 4
python3 sender.py --protocol gbn --window 4 --input input.txt --p-error 0.0 --p-loss 0.0 --delay 10

# Window = 8
python3 sender.py --protocol gbn --window 8 --input input.txt --p-error 0.0 --p-loss 0.0 --delay 10
```

---

## Protocol 3: Selective Repeat (SR)

### Clean channel with window size 4

**Terminal A:**
```bash
python3 receiver.py --protocol sr --window 4 --output output_sr.txt --verbose
```

**Terminal B:**
```bash
python3 sender.py --protocol sr --window 4 --input input.txt --p-error 0.0 --p-loss 0.0 --delay 10 --verbose
```

**What to watch:** Receiver sends independent ACKs for each frame. Out-of-order frames are buffered, not discarded.

---

### With errors (p-error = 0.3)

**Terminal A:**
```bash
python3 receiver.py --protocol sr --window 4 --output output_sr_err.txt --verbose
```

**Terminal B:**
```bash
python3 sender.py --protocol sr --window 4 --input input.txt --p-error 0.3 --p-loss 0.0 --delay 10 --verbose
```

**What to watch:** When a frame is corrupted, receiver sends NAK. Sender retransmits **only that frame**. Compare retransmissions to GBN at the same error rate — SR should be significantly lower.

---

## 📊 Step 3 — Comparative Testing (Assignment Test Cases)

Run all three protocols with the **same parameters** and record the output.

### Test Case 1: No errors (baseline efficiency)

```bash
# SAW
python3 receiver.py --protocol saw --output out_saw.txt &
python3 sender.py   --protocol saw --input input.txt --p-error 0 --p-loss 0 --delay 5

# GBN (N=4)
python3 receiver.py --protocol gbn --output out_gbn.txt &
python3 sender.py   --protocol gbn --window 4 --input input.txt --p-error 0 --p-loss 0 --delay 5

# SR (N=4)
python3 receiver.py --protocol sr --window 4 --output out_sr.txt &
python3 sender.py   --protocol sr --window 4 --input input.txt --p-error 0 --p-loss 0 --delay 5
```

**Record:** Total time, Throughput, Efficiency (should all be ~100% with no errors).

---

### Test Case 2: Error probability sweep

Run each protocol with `--p-error` from 0.1 to 0.5 in steps of 0.1:

```bash
for P in 0.1 0.2 0.3 0.4 0.5; do
  echo "=== p_error = $P ==="

  python3 receiver.py --protocol saw --output /dev/null &
  python3 sender.py --protocol saw --input input.txt --p-error $P --p-loss 0 --delay 5

  python3 receiver.py --protocol gbn --output /dev/null &
  python3 sender.py --protocol gbn --window 4 --input input.txt --p-error $P --p-loss 0 --delay 5

  python3 receiver.py --protocol sr --window 4 --output /dev/null &
  python3 sender.py --protocol sr --window 4 --input input.txt --p-error $P --p-loss 0 --delay 5
done
```

**Record:** Retransmissions and Efficiency for each (protocol, p) pair.

---

### Test Case 3: Loss probability sweep

```bash
for P in 0.1 0.2 0.3 0.4 0.5; do
  echo "=== p_loss = $P ==="

  python3 receiver.py --protocol saw --output /dev/null &
  python3 sender.py --protocol saw --input input.txt --p-error 0 --p-loss $P --delay 5 --timeout 200

  python3 receiver.py --protocol gbn --output /dev/null &
  python3 sender.py --protocol gbn --window 4 --input input.txt --p-error 0 --p-loss $P --delay 5 --timeout 200

  python3 receiver.py --protocol sr --window 4 --output /dev/null &
  python3 sender.py --protocol sr --window 4 --input input.txt --p-error 0 --p-loss $P --delay 5 --timeout 200
done
```

---

### Test Case 4: RTT comparison

Enable `--verbose` on sender and note the `RTT=` values printed for each ACK:

```bash
python3 receiver.py --protocol saw --output /dev/null &
python3 sender.py --protocol saw --input input.txt --p-error 0 --p-loss 0 --delay 20 --verbose 2>&1 | grep "RTT="
```

**Compare:** Average RTT for SAW vs. GBN vs. SR (should be similar since RTT is a channel property, but window protocols have lower *effective* per-frame wait time).

---

## ✔️ Step 4 — Verify Correctness

After any transfer, verify the received output is identical to the input:

```bash
# Binary comparison (exact match)
cmp input.txt output.txt && echo "✓ Files match" || echo "✗ Files differ"

# Or with diff (human-readable)
diff input.txt output.txt && echo "✓ No differences" || echo "✗ Differences found"

# Or via Python (strips padding zeros from last chunk)
python3 -c "
import sys
orig = open('input.txt','rb').read()
recv = open('output.txt','rb').read()
recv_trimmed = recv[:len(orig)]
if recv_trimmed == orig:
    print('✓ Content matches (ignoring padding)')
else:
    print('✗ Content mismatch')
    # Show first difference
    for i,(a,b) in enumerate(zip(orig, recv_trimmed)):
        if a != b:
            print(f'  First diff at byte {i}: expected {a:#04x}, got {b:#04x}')
            break
"
```

> **Note:** The received file may be slightly larger than the input due to zero-padding of the last frame. The trimmed comparison above handles this correctly.

---

## 🛠️ Step 5 — Command-Line Reference

### receiver.py options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--protocol` | `saw\|gbn\|sr` | `saw` | ARQ protocol |
| `--window` | int | `4` | Receiver window size (SR only) |
| `--host` | str | `127.0.0.1` | Bind IP address |
| `--port` | int | `5001` | TCP port to listen on |
| `--output` | str | `output.txt` | Output file for received data |
| `--payload` | int | `46` | Payload bytes per frame (must match sender) |
| `--verbose` | flag | off | Per-frame debug output |

### sender.py options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--protocol` | `saw\|gbn\|sr` | `saw` | ARQ protocol |
| `--window` | int | `4` | Sender window size |
| `--host` | str | `127.0.0.1` | Receiver IP address |
| `--port` | int | `5001` | Receiver port |
| `--input` | str | `input.txt` | File to transmit |
| `--payload` | int | `46` | Payload bytes per frame |
| `--p-error` | float | `0.0` | Bit-error probability per frame |
| `--p-loss` | float | `0.0` | Frame-loss probability |
| `--delay` | float | `50.0` | Max channel delay in ms |
| `--timeout` | float | `500.0` | Initial RTO in ms |
| `--verbose` | flag | off | Per-frame debug output |

---

## ⚠️ Common Issues & Fixes

| Problem | Cause | Fix |
|---------|-------|-----|
| `ConnectionRefusedError` | Sender started before Receiver | Always start Receiver **first** |
| Transfer hangs forever | `--timeout` too large, no retransmits | Lower `--timeout` (try `200`) |
| Files don't match | `--payload` mismatch between sender and receiver | Use the same `--payload` value on both sides |
| `Address already in use` | Previous run left socket open | Wait 30 s or use `--port 5002` |
| Receiver prints nothing | `--verbose` not enabled | Add `--verbose` flag |
| Low efficiency at low error | `--delay` too high relative to `--timeout` | Reduce `--delay` or increase `--timeout` |

---

## 📈 Expected Metrics for Analysis

When running with `input.txt` (2730 bytes ≈ 60 frames at 46 B/frame):

### Zero errors (p=0, delay=10ms)

| Protocol | Window | Retransmits | Efficiency | Notes |
|----------|--------|-------------|------------|-------|
| SAW | 1 | 0 | ~100% | Baseline |
| GBN | 4 | 0 | ~100% | Faster than SAW |
| SR | 4 | 0 | ~100% | Fastest |

### p-error = 0.3

| Protocol | Window | Retransmits (approx) | Efficiency (approx) |
|----------|--------|----------------------|---------------------|
| SAW | 1 | ~18 | ~70% |
| GBN | 4 | ~50 | ~50% |
| SR | 4 | ~18 | ~70% |

> GBN retransmits the **entire window** on each error → much worse than SR at high error rates.

---

## 🔑 Module Import Map

```
sender.py / receiver.py
    ├── channel.py
    │       └── error_injection.py   (introduce_random_bit_flip)
    ├── frame.py
    │       └── error_detection.py   (compute_crc, verify_crc, fcs_to_bytes, bytes_to_fcs)
    └── timer.py
```

---

*Testing guide for Assignment 2 — Data Communications & Networks*
*Last updated: 2026-08-25*
