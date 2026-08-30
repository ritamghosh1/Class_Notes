# 📡 Data Communications — Assignment 2
## Data Link Layer: Framing, Error Control & Flow Control Protocols

> **Course**: Data Communications & Networks
> **Topic**: Data Link Layer — ARQ Protocols (Stop-and-Wait, Go-Back-N, Selective Repeat)
> **Prerequisites**: Assignment 1 (CRC/Checksum & Error Injection modules)

---

## 📋 Table of Contents

1. [What We Have To Do](#1-what-we-have-to-do)
2. [Core Concepts & Theory](#2-core-concepts--theory)
   - [Data Link Layer Overview](#21-data-link-layer-overview)
   - [Framing](#22-framing)
   - [MAC Addresses](#23-mac-addresses)
   - [CRC & Checksum](#24-crc--checksum)
   - [Error Control](#25-error-control)
   - [Flow Control](#26-flow-control)
   - [Stop-and-Wait ARQ](#27-stop-and-wait-arq)
   - [Go-Back-N ARQ](#28-go-back-n-arq)
   - [Selective Repeat ARQ](#29-selective-repeat-arq)
   - [Channel Characteristics](#210-channel-characteristics)
   - [Timers & Timeouts (RTT)](#211-timers--timeouts-rtt)
   - [Sliding Window Protocol](#212-sliding-window-protocol)
3. [Things We Need to Know (Conceptual)](#3-things-we-need-to-know-conceptual)
4. [Approach & Strategy](#4-approach--strategy)
5. [Implementation Plan](#5-implementation-plan)
6. [Testing & Evaluation Plan](#6-testing--evaluation-plan)
7. [Expected Results & Analysis](#7-expected-results--analysis)

---

## 1. What We Have To Do

This assignment asks us to simulate the **Data Link Layer** of a computer network. We are building two programs — a **Sender** and a **Receiver** — that communicate via a **socket connection**, with a simulated noisy/lossy **Channel** in between.

### High-Level Summary

| Component | What it does |
|-----------|-------------|
| `Framing()` | Packs raw data into structured Ethernet-like frames with header, payload, and FCS trailer |
| `Channel()` | Simulates a real-world network channel: introduces bit errors and random delays |
| `Send()` | Sender transmits frames; decides whether to send new frames or retransmit |
| `Recv()` (Sender-side) | Processes incoming ACKs and updates the window/state |
| `Timer()` | Tracks per-frame transmission time |
| `Timeout()` | Computes RTT and dynamically recalculates the timeout threshold |
| `Recv()` (Receiver-side) | Receives data frames, buffers or discards based on order and correctness |
| `Check()` | Verifies frame integrity using CRC/Checksum from Assignment 1 |
| `Send()` (Receiver-side) | Sends ACK/NAK packets back to sender |

### Three Flow Control Protocols to Implement

```
1. Stop-and-Wait ARQ   (Window size = 1, simplest)
2. Go-Back-N ARQ       (Sender window = N, Recv window = 1)
3. Selective Repeat ARQ (Sender window = N, Recv window = N)
```

### What We Must Test

- Round-trip time comparison across all three protocols
- Efficiency without any errors or frame loss
- Efficiency with error/delay probability ranging from 0.1 to 0.5

---

## 2. Core Concepts & Theory

### 2.1 Data Link Layer Overview

The **Data Link Layer** (Layer 2 of the OSI model) is responsible for:

- **Framing**: Packaging raw bits from the physical layer into manageable units called *frames*
- **Physical Addressing**: Using MAC addresses to identify sender and receiver on the same network segment
- **Error Detection & Correction**: Detecting (and sometimes correcting) transmission errors
- **Flow Control**: Preventing the sender from overwhelming the receiver
- **Access Control**: Managing who can use the shared channel at any given time

The Data Link Layer handles **hop-to-hop** (not end-to-end) delivery, sitting between the Network Layer (IP) above and the Physical Layer below.

```
OSI Layer Stack:
+-----------------------+
|  Application (L7)     |
+-----------------------+
|  Transport (L4)       |   <- TCP/UDP handles end-to-end
+-----------------------+
|  Network (L3)         |   <- IP handles routing
+-----------------------+
|  Data Link (L2)       |   <- OUR FOCUS: MAC, Framing, ARQ
+-----------------------+
|  Physical (L1)        |
+-----------------------+
```

---

### 2.2 Framing

**Framing** is the process of dividing a continuous stream of bits into discrete, bounded units called **frames**. This allows the receiver to know where one frame ends and the next begins.

#### Our Frame Structure

```
+------------------------------------------------------------------+
|  HEADER (15 bytes)          |  PAYLOAD (46-1500 bytes) | TRAILER |
|                             |                          | (4 B)   |
| Src MAC | Dst MAC | Len | # |  Data from input file    |  FCS    |
|  6 bytes|  6 bytes| 2 B | 1B|                          |         |
+------------------------------------------------------------------+
```

| Field | Size | Description |
|-------|------|-------------|
| Source MAC Address | 6 bytes | Hardware address of the sending NIC |
| Destination MAC Address | 6 bytes | Hardware address of the receiving NIC |
| Length | 2 bytes | Size of the payload in bytes |
| Frame Sequence Number | 1 byte | Identifies frames (0-255, wraps around) |
| Payload (Data) | 46-1500 bytes | Chunk of the input text file |
| FCS (Trailer) | 4 bytes | CRC-32 or Checksum output |

> **Why minimum 46 bytes payload?** From Ethernet standards — to reliably detect collisions, a minimum frame size is required. Any payload shorter than 46 bytes must be **padded** to 46 bytes.

> **Why maximum 1500 bytes?** This is the standard **MTU (Maximum Transmission Unit)** for Ethernet.

#### Framing Process — Step by Step

```
Input File
    |
    v
Split into chunks of fixed size (e.g., 46 bytes)
    |
    v
For each chunk:
  +----------------------------+
  | Prepend Header             |
  | (MAC src, MAC dst, len,    |
  |  seq_no)                   |
  +------------+---------------+
               |
  +------------v---------------+
  | Compute FCS on             |
  | (Header + Payload)         |
  | using CRC/Checksum (A1)    |
  +------------+---------------+
               |
  +------------v---------------+
  | Append FCS as Trailer      |
  +----------------------------+
  Final Frame ready to send
```

---

### 2.3 MAC Addresses

A **MAC (Media Access Control) address** is a 48-bit (6-byte) hardware identifier assigned to a Network Interface Card (NIC). Written in hexadecimal notation:

```
Example: AA:BB:CC:DD:EE:FF
```

- **Globally unique** (in real hardware; we simulate them)
- Used for communication within the **same network segment** (local LAN)
- Unlike IP addresses, MAC addresses do not change when you move networks
- **Broadcast address**: `FF:FF:FF:FF:FF:FF` — sent to all devices on the segment

In our simulation, we will **assign fixed MAC addresses** to our Sender and Receiver programs embedded in the frame header.

---

### 2.4 CRC & Checksum

We **reuse the CRC/Checksum module from Assignment 1** as-is.

#### CRC (Cyclic Redundancy Check)

- Based on **polynomial division** in GF(2) (binary arithmetic without carries)
- A **generator polynomial** (e.g., CRC-32: `0x04C11DB7`) is chosen
- The remainder of the division is appended as the FCS
- At the receiver, dividing (data + FCS) by the same polynomial yields a **zero remainder** if no error

```
CRC Process:
Data bits -> Append 'r' zeros (r = degree of generator) -> Divide by Generator Polynomial
                                                               |
                                                         Remainder = CRC
```

#### Checksum

- The data is divided into fixed-size chunks (e.g., 16-bit words)
- All chunks are added together in **one's complement arithmetic**
- The **one's complement of the sum** is the checksum
- At the receiver, sum all chunks including the checksum — if result is all 1s, no error

#### Why CRC is Better

| Property | Checksum | CRC |
|----------|----------|-----|
| Error detection | Single-bit, some burst | All single-bit, all 2-bit, all odd-bit, burst <= r bits |
| Computational cost | Very low | Moderate |
| Standard use | IP, UDP headers | Ethernet, TCP (option), disk storage |

---

### 2.5 Error Control

**Error control** detects and handles errors during transmission.

#### Error Detection

Done at the receiver using **FCS** (CRC or Checksum). If an error is detected, the frame is **discarded silently** (in SAW and GBN) or a **NAK** may be sent (in Selective Repeat).

#### Error Recovery — ARQ (Automatic Repeat reQuest)

When a frame is lost or corrupted, the sender must retransmit it. The three ARQ schemes we implement define *when* and *which* frames to retransmit.

---

### 2.6 Flow Control

**Flow Control** prevents the sender from overwhelming the receiver with data faster than it can process. The mechanism we use is **feedback-based flow control** via acknowledgments (ACKs) and a sliding window.

#### Efficiency Definition

```
Efficiency (eta) = Useful data sent / Total channel capacity used

For Stop-and-Wait:
  eta = T_frame / (T_frame + T_prop + T_proc + T_ack)

Key parameter 'a' = propagation delay / transmission time:
  If a >> 1: channel is mostly idle -> low efficiency (SAW suffers badly)
  If a << 1: channel is kept busy   -> high efficiency
```

---

### 2.7 Stop-and-Wait ARQ

#### Concept

The sender transmits **one frame at a time** and waits for an ACK before transmitting the next.

```
Sender                              Receiver
  |                                    |
  |---- Frame 0 ---------------------->|
  |                                    |-- Check FCS
  |                                    |-- Accept Frame
  |<--- ACK 0 -------------------------|
  |                                    |
  |---- Frame 1 ---------------------->|
```

#### Timeout Scenario (Frame Lost)

```
Sender                              Receiver
  |                                    |
  |---- Frame 0 ----X (LOST)          |
  |                                    |
  |  [TIMEOUT FIRES]                   |
  |---- Frame 0 (Retransmit) -------->|
  |<--- ACK 0 -------------------------|
```

#### Key Properties

| Property | Value |
|----------|-------|
| Sender window size | 1 |
| Receiver window size | 1 |
| Sequence numbers needed | 2 (alternates between 0 and 1) |
| Efficiency (no errors) | `1 / (1 + 2a)` |
| Efficiency (error prob. p) | `(1-p) / (1 + 2a)` |

#### Pros and Cons

- ✅ Simple to implement, minimal buffering
- ❌ Very inefficient for large propagation delays (satellite/WAN links)
- ❌ One lost frame causes long channel idle time

---

### 2.8 Go-Back-N ARQ

#### Concept

The sender can send up to **N frames** (the window size) without waiting for an ACK. The receiver only accepts **in-order frames** — out-of-order frames are discarded.

```
Sender Window (N=4):
+---+---+---+---+
| 0 | 1 | 2 | 3 |  <- All sent, waiting for ACKs
+---+---+---+---+

When ACK 0 arrives:
+---+---+---+---+
| 1 | 2 | 3 | 4 |  <- Window slides forward
+---+---+---+---+
```

#### Cumulative ACK

ACK number `n` means: "I have received all frames up to and including frame `n`."

```
Sender                              Receiver
  |---- Frame 0 ---------------------->|
  |---- Frame 1 ---------------------->|
  |---- Frame 2 --------X (LOST)      |
  |---- Frame 3 ---------------------->| (Discarded! Out of order)
  |<--- ACK 1 -------------------------| (ACK for 0 and 1 only)
  |                                    |
  |  [TIMEOUT on Frame 2]              |
  |---- Frame 2 (Retransmit) -------->|
  |---- Frame 3 (Retransmit) -------->| <- Must resend 3 too!
```

#### Key Properties

| Property | Value |
|----------|-------|
| Sender window size | N |
| Receiver window size | 1 |
| Sequence numbers needed | At least N+1 |
| Efficiency (no errors) | `N/(1+2a)` if N >= 1+2a, else `1` |

#### Pros and Cons

- ✅ Better throughput than Stop-and-Wait
- ✅ Simple receiver (no buffering of out-of-order frames)
- ❌ On error, **entire window** is retransmitted (wasteful at high error rates)

---

### 2.9 Selective Repeat ARQ

#### Concept

Both sender and receiver have a window of size **N**. The receiver can accept and **buffer out-of-order frames**. When a frame is lost, **only that specific frame** is retransmitted.

```
Sender Window (N=4): Frame 2 is lost
+---+----+---+---+
| 0 | XX | 3 | 4 |  <- 0, 3, 4 buffered at receiver; 2 missing
+---+----+---+---+

After Frame 0 ACK arrives, window slides.
Sender retransmits ONLY Frame 2.
```

#### Independent ACK

Each frame is acknowledged **independently**:
- ACK 3 means "Frame 3 received" — it says nothing about frames 0, 1, 2.

#### NAK (Negative Acknowledgement)

- When the receiver detects a corrupted frame, it sends a NAK for that specific frame
- The sender retransmits **immediately** without waiting for timeout
- Faster error recovery than pure timeout-based retransmission

#### Key Properties

| Property | Value |
|----------|-------|
| Sender window size | N |
| Receiver window size | N |
| Sequence numbers needed | At least 2N |
| Efficiency (error prob. p) | `(1-p)` — much better than GBN at high error rates |

#### Why 2N Sequence Numbers?

With only N sequence numbers, the receiver cannot distinguish between a **new frame** and a **retransmitted old frame** when the window wraps around. Using 2N sequence numbers prevents this ambiguity.

#### Pros and Cons

- ✅ Most efficient — only lost frames retransmitted
- ✅ Works well even at high error rates
- ❌ Complex receiver (must buffer and sort out-of-order frames)
- ❌ Requires more receiver memory

---

### 2.10 Channel Characteristics

The **Channel** simulates a real-world transmission medium with two failure modes:

#### Bit Errors

Caused by noise or signal attenuation. In our simulation:
- We use the **error injection module from Assignment 1**
- Error probability `p_error` in [0.1, 0.5]
- A bit error flips bits in the frame, making the FCS check fail at the receiver

#### Packet Loss (Delay-induced)

Caused by congestion, routing failures, or extreme propagation delay:
- We model this as **random delay** exceeding the timeout threshold
- Loss probability `p_loss` in [0.1, 0.5]

```
Frame Journey Through Channel:
Frame -> [Random Delay?] -> [Bit Error?] -> Receiver
  |                                           |
  |  If delay > timeout: Sender retransmits   |
  |  If bit error: Receiver discards frame    |
```

---

### 2.11 Timers & Timeouts (RTT)

#### Why Timers?

Without timers, if a frame or ACK is lost, the sender would wait forever. **Timers** bound the maximum wait time and trigger retransmission.

#### RTT — Round-Trip Time

RTT is the time from when a frame is sent to when its ACK is received:

```
RTT = 2 x T_prop + T_frame + T_ack + T_processing

Timeline:
t=0         : Sender transmits frame
t=T_prop    : Frame arrives at receiver
t=T_prop+Tp : Receiver finishes processing, sends ACK
t=2*T_prop+Tp+T_ack : ACK arrives at sender
```

#### Adaptive Timeout (Simplified TCP approach)

```
Estimated_RTT = (1 - alpha) x Estimated_RTT + alpha x Sample_RTT
                where alpha = 0.125

Deviation = (1 - beta) x Deviation + beta x |Sample_RTT - Estimated_RTT|
            where beta = 0.25

Timeout = Estimated_RTT + 4 x Deviation
```

- Record send time when frame is transmitted
- Record receive time when ACK arrives
- Compute sample RTT, then update timeout using the EWMA formula above

#### Timer per Frame

Each frame in flight has its own timer:
- **Stop-and-Wait**: one global timer
- **Go-Back-N**: timer on the oldest unACKed frame; on timeout, retransmit whole window
- **Selective Repeat**: independent timer per unACKed frame

---

### 2.12 Sliding Window Protocol

The **Sliding Window** is the abstraction underlying Go-Back-N and Selective Repeat.

```
Conceptual Window:

[Sent & Acked] [Sent, Not Acked] [Not Yet Sent] [Future]
---------------[################][==============]--------
                <- Window Size N ->

As ACKs arrive, the window "slides" to the right:

Before ACK 0:  [0][1][2][3] | [4][5]...
After ACK 0:   [1][2][3][4] | [5][6]...
```

#### Window Size and Throughput

```
Throughput = min(N x Frame_size / RTT, Link_bandwidth)

Optimal N = (Bandwidth x RTT) / Frame_size
           = Bandwidth-Delay Product / Frame_size
```

---

## 3. Things We Need to Know (Conceptual)

Before starting implementation, solidify these concepts:

### Networking Fundamentals
- [ ] OSI Model layers and their responsibilities
- [ ] Difference between Layer 2 (Data Link) and Layer 3 (Network)
- [ ] What a MAC address is and how it differs from an IP address
- [ ] What MTU means and why frames have size limits

### ARQ Protocol Theory
- [ ] Why sequence numbers are necessary
- [ ] How window size affects throughput
- [ ] Difference between cumulative ACK (GBN) and independent ACK (SR)
- [ ] Why Selective Repeat needs 2N sequence numbers but GBN needs only N+1
- [ ] NAK vs. timeout-based retransmission — trade-offs

### Error Detection
- [ ] How CRC works (polynomial division in GF(2))
- [ ] How Checksum works (one's complement addition)
- [ ] Why CRC is more powerful than checksum
- [ ] What the FCS (Frame Check Sequence) field contains

### Timer & RTT Theory
- [ ] What propagation delay, transmission delay, and processing delay are
- [ ] How RTT is measured and why it varies
- [ ] Why adaptive timeouts are better than fixed timeouts
- [ ] What happens when the timeout is too small vs. too large

### Efficiency & Performance Metrics
- [ ] Formula for Stop-and-Wait efficiency: `eta = 1 / (1 + 2a)`
- [ ] Formula for sliding window efficiency: `eta = N / (1 + 2a)` when N < 1+2a
- [ ] How error probability degrades efficiency differently for GBN vs. SR
- [ ] Bandwidth-Delay Product and its role in optimal window sizing

### Socket Programming
- [ ] TCP vs. UDP sockets (we use TCP for reliable transport; our simulation adds unreliability on top)
- [ ] How `send()`, `recv()`, `bind()`, `listen()`, `accept()`, `connect()` work
- [ ] Blocking vs. non-blocking sockets
- [ ] How to implement timeouts on `recv()` using `select()` or `SO_RCVTIMEO`

---

## 4. Approach & Strategy

### Overall Architecture

```
+------------------------------------+  Socket  +-----------------------------------+
|         SENDER PROGRAM             |<-------->|       RECEIVER PROGRAM            |
|                                    |          |                                   |
| +--------+  +-------------------+  |          | +-------+   +------------------+ |
| |Input   |->| Framing()         |  |          | |Recv() |-> | Check()          | |
| |File    |  | (pack frame)      |  |          | |       |   | (verify FCS)     | |
| +--------+  +--------+----------+  |          | +---+---+   +--------+---------+ |
|                      |             |          |     |                |           |
| +--------------------v-----------+ |  Frames  | +---v---------------v---------+ |
| | Send() + FlowControl Logic     |-+---------►| | Accept / Buffer / Discard   | |
| | (Stop&Wait / GBN / SR)        | |          | +-------------------+---------+ |
| +--------+----------+-----------+ |  ACKs    |                     |           |
|          |          |             |◄---------+--  Send() (ACK/NAK) +           |
| +---------+  +-------+----------+ |          +-----------------------------------+
| | Timer() |  | Recv() ACK proc  | |
| | Timeout()|  | (update window)  | |
| +---------+  +------------------+ |
|                                    |
|      Channel() wraps socket        |
|  (injects delay + bit errors)      |
+------------------------------------+
```

### Modular Design Strategy

```
project/
+-- assignment1/          <- Reuse from Assignment 1
|   +-- crc.py
|   +-- checksum.py
|   +-- error_inject.py
|
+-- frame.py              <- Framing() - build/parse frames
+-- channel.py            <- Channel() - delay + error simulation
+-- timer.py              <- Timer() + Timeout() - RTT computation
+-- sender.py             <- Sender program (all three protocols)
+-- receiver.py           <- Receiver program (all three protocols)
+-- test_runner.py        <- Automated testing + metrics collection
+-- input.txt             <- Test input file
```

### Protocol Selection Strategy

Implement the three protocols as configurable modes so that `sender.py` and `receiver.py` can run any protocol without code duplication:

```python
# Pseudo-code concept
def Send(protocol="stop_and_wait", window_size=1):
    if protocol == "stop_and_wait":
        run_saw()
    elif protocol == "go_back_n":
        run_gbn(N=window_size)
    elif protocol == "selective_repeat":
        run_sr(N=window_size)
```

### Error/Loss Injection Strategy

- Each frame and ACK transmission gets a random probability check
- `if random() < p_error`: flip bits using Assignment 1 error injector
- `if random() < p_delay`: add extra delay (possibly exceeding timeout)
- These probabilities are passed as configurable command-line parameters

### Logging & Metrics Strategy

Every event is logged with a timestamp:

```
[t=0.0012s] SENDER: Sending Frame #3, Seq=3, Size=46 bytes
[t=0.0023s] CHANNEL: Frame #3 - No error, delay=0.8ms
[t=0.0031s] RECEIVER: Frame #3 received, FCS OK -> ACK 3
[t=0.0042s] SENDER: ACK 3 received, RTT=3.0ms, New Timeout=6.0ms
```

This enables computing:
- Total transmission time
- Number of retransmissions
- Effective throughput
- Channel utilization (efficiency)

---

## 5. Implementation Plan

### Phase 0: Setup & Reuse (Assignment 1 Integration)

**Goal**: Confirm CRC/Checksum and error injection modules work correctly.

- [ ] Locate Assignment 1 modules: `crc.py`, `checksum.py`, `error_inject.py`
- [ ] Write unit tests for CRC: known input -> known CRC output
- [ ] Write unit tests for Checksum: known input -> known checksum output
- [ ] Confirm `inject_error(frame, probability)` works correctly
- [ ] Create `assignment1/` import structure

**Deliverable**: Passing unit tests for all Assignment 1 modules

---

### Phase 1: Frame Module

**Goal**: Implement `Framing()` to build and parse Ethernet-like frames.

#### 1.1 — Define Frame Constants

```python
PAYLOAD_SIZE = 46          # Fixed payload size (within 46-1500)
MAC_SRC = "AA:BB:CC:DD:EE:01"
MAC_DST = "AA:BB:CC:DD:EE:02"
HEADER_SIZE = 15           # 6 + 6 + 2 + 1
FCS_SIZE = 4
FRAME_SIZE = HEADER_SIZE + PAYLOAD_SIZE + FCS_SIZE
```

#### 1.2 — `build_frame(seq_no, payload)` function

Steps:
1. Encode source MAC (6 bytes)
2. Encode destination MAC (6 bytes)
3. Encode payload length as 2-byte big-endian integer
4. Encode sequence number as 1 byte
5. If `len(payload) < PAYLOAD_SIZE`, pad with zero bytes
6. Compute CRC/Checksum over (header + payload)
7. Append 4-byte FCS
8. Return complete byte string

#### 1.3 — `parse_frame(raw_bytes)` function

Steps:
1. Extract MAC src (bytes 0-5)
2. Extract MAC dst (bytes 6-11)
3. Extract length (bytes 12-13)
4. Extract seq_no (byte 14)
5. Extract payload (bytes 15 to 15+length)
6. Extract FCS (last 4 bytes)
7. Return structured dictionary/object

#### 1.4 — `read_file_chunks(filename, chunk_size)` generator

- Opens the input text file
- Yields chunks of `chunk_size` bytes (padded if necessary)
- Stops when file is exhausted

**Deliverable**: `frame.py` with build, parse, and file-reading functions + unit tests

---

### Phase 2: Channel Module

**Goal**: Implement `Channel()` to simulate a noisy, lossy network channel.

#### 2.1 — `Channel` class parameters

```python
class Channel:
    def __init__(self, error_prob=0.0, loss_prob=0.0, max_delay_ms=50):
        self.error_prob = error_prob    # Probability of bit error
        self.loss_prob  = loss_prob     # Probability of complete frame loss
        self.max_delay  = max_delay_ms  # Maximum random delay in ms
```

#### 2.2 — `transmit(frame_bytes)` method

Steps:
1. Check if frame is **lost**: `if random() < loss_prob -> return None`
2. Inject random **delay**: `time.sleep(random() * max_delay / 1000)`
3. Check if **bit error** occurs: `if random() < error_prob -> frame = inject_error(frame)`
4. Return (possibly corrupted) frame bytes

**Deliverable**: `channel.py` with parameterized Channel class + unit tests

---

### Phase 3: Timer Module

**Goal**: Implement `Timer()` and `Timeout()` with adaptive RTT estimation.

#### 3.1 — `FrameTimer` class

```python
class FrameTimer:
    def __init__(self, initial_timeout_ms=200):
        self.timeout = initial_timeout_ms
        self.est_rtt = initial_timeout_ms / 4
        self.dev_rtt = 0
        self.send_times = {}      # seq_no -> send_time
```

#### 3.2 — `start(seq_no)` method

- Records `send_times[seq_no] = time.time()`

#### 3.3 — `stop(seq_no)` method

- Computes `sample_rtt = time.time() - send_times[seq_no]`
- Removes `seq_no` from `send_times`

#### 3.4 — `update_timeout(sample_rtt)` method (Adaptive)

```
est_rtt = 0.875 x est_rtt + 0.125 x sample_rtt
dev_rtt = 0.75 x dev_rtt + 0.25 x |sample_rtt - est_rtt|
timeout = est_rtt + 4 x dev_rtt
```

#### 3.5 — `is_expired(seq_no)` method

- Returns `True` if `time.time() - send_times[seq_no] > timeout`

**Deliverable**: `timer.py` with FrameTimer class + unit tests

---

### Phase 4: Socket Infrastructure

**Goal**: Set up TCP socket communication between Sender and Receiver.

#### 4.1 — Receiver socket setup

```
1. Create TCP socket
2. Bind to (HOST, PORT)
3. Listen for connection
4. Accept connection from sender
5. Enter receive loop
```

#### 4.2 — Sender socket setup

```
1. Create TCP socket
2. Connect to (HOST, PORT) of receiver
3. Enter send loop
```

#### 4.3 — Length-prefixed framing over TCP

TCP is a **stream protocol** and does not preserve message boundaries. Prefix each frame with its length:

```
Over-the-wire format:
+-------------+----------------------------+
|  4 bytes    |  N bytes                   |
|  Length (N) |  Frame data                |
+-------------+----------------------------+
```

#### 4.4 — ACK frame structure

```python
# Simple ACK: 2 bytes
# Byte 0: Flag  (0x01 = ACK, 0x00 = NAK)
# Byte 1: Sequence number being acknowledged
```

**Deliverable**: Working TCP echo test before adding protocol logic

---

### Phase 5: Stop-and-Wait Protocol

**Goal**: End-to-end implementation of the simplest ARQ protocol.

#### Sender Logic

```
seq_no = 0
For each chunk in file:
    frame = build_frame(seq_no, chunk)
    
    LOOP:
        channel.transmit(frame) -> socket
        timer.start(seq_no)
        
        WAIT for ACK with timeout:
            if ACK received and ACK.seq == seq_no:
                timer.stop(seq_no)
                timer.update_timeout(sample_rtt)
                break LOOP
            elif timeout:
                log("Timeout! Retransmitting frame", seq_no)
                # continue LOOP -> retransmit
    
    seq_no = 1 - seq_no    # Toggle between 0 and 1
```

#### Receiver Logic

```
expected_seq = 0
LOOP:
    raw_frame = socket.recv()
    frame = parse_frame(raw_frame)
    
    if Check(frame) == ERROR:
        discard frame
        # No ACK sent -> sender will timeout
        continue
    
    if frame.seq_no != expected_seq:
        # Duplicate frame -> re-ACK last accepted
        send_ack(1 - expected_seq)
        continue
    
    accept frame, deliver payload
    send_ack(expected_seq)
    expected_seq = 1 - expected_seq
```

**Deliverable**: Working Stop-and-Wait with correct timeout and metrics logging

---

### Phase 6: Go-Back-N Protocol

**Goal**: Sliding window with N frames in flight, in-order delivery at receiver.

#### Sender Logic

```
base = 0          # Oldest unACKed frame
next_seq = 0      # Next frame to send
window = {}       # seq_no -> frame (for retransmission)

THREAD 1 (Sender):
    while data to send and next_seq < base + N:
        frame = build_frame(next_seq, next_chunk())
        window[next_seq] = frame
        channel.transmit(frame) -> socket
        timer.start(next_seq)
        next_seq += 1

THREAD 2 (ACK receiver):
    ack = recv_ack()
    if valid cumulative ACK for ack.seq:
        for seq in range(base, ack.seq + 1):
            timer.stop(seq)
            del window[seq]
        base = ack.seq + 1
        timer.update_timeout(sample_rtt)

THREAD 3 (Timeout checker):
    if timer.is_expired(base):
        # Retransmit entire window
        for seq in range(base, next_seq):
            channel.transmit(window[seq]) -> socket
            timer.start(seq)  # restart timer
```

#### Receiver Logic

```
expected_seq = 0
LOOP:
    raw_frame = socket.recv()
    frame = parse_frame(raw_frame)
    
    if Check(frame) == ERROR or frame.seq_no != expected_seq:
        discard frame
        # Send cumulative ACK for last accepted
        if expected_seq > 0:
            send_ack(expected_seq - 1)
        continue
    
    accept frame, deliver payload
    send_ack(expected_seq)
    expected_seq += 1
```

**Deliverable**: Working Go-Back-N with configurable N and correct window management

---

### Phase 7: Selective Repeat Protocol

**Goal**: Both sender and receiver have window N; only lost frames retransmitted.

#### Sender Logic

```
base = 0
next_seq = 0
window = {}             # seq_no -> (frame, is_acked)
per_frame_timers = {}

THREAD 1 (Sender):
    while next_seq < base + N and data available:
        frame = build_frame(next_seq, next_chunk())
        window[next_seq] = (frame, False)
        channel.transmit(frame)
        per_frame_timers[next_seq] = start_timer(next_seq)
        next_seq += 1

THREAD 2 (ACK/NAK receiver):
    pkt = recv_ack()
    if pkt.type == ACK:
        mark window[pkt.seq] as ACKED
        per_frame_timers[pkt.seq].stop()
        update_timeout(sample_rtt)
        # Slide window: advance base past all consecutive ACKED frames
        while window[base].is_acked:
            del window[base]
            base += 1
    elif pkt.type == NAK:
        channel.transmit(window[pkt.seq].frame)  # Retransmit immediately
        per_frame_timers[pkt.seq].restart()

THREAD 3 (Per-frame timeout checker):
    for seq_no in per_frame_timers:
        if timer.is_expired(seq_no) and not window[seq_no].is_acked:
            channel.transmit(window[seq_no].frame)
            per_frame_timers[seq_no].restart()
```

#### Receiver Logic

```
recv_base = 0
recv_buffer = {}    # seq_no -> frame (out-of-order buffer)

LOOP:
    raw_frame = socket.recv()
    frame = parse_frame(raw_frame)
    
    if Check(frame) == ERROR:
        send_nak(frame.seq_no)    # Optional NAK
        continue
    
    seq = frame.seq_no
    
    if recv_base <= seq < recv_base + N:
        recv_buffer[seq] = frame
        send_ack(seq)             # Independent ACK
        
        # Deliver in-order frames to output
        while recv_base in recv_buffer:
            deliver(recv_buffer[recv_base].payload)
            del recv_buffer[recv_base]
            recv_base += 1
    
    elif recv_base - N <= seq < recv_base:
        # Already received duplicate -> re-ACK
        send_ack(seq)
    # else: outside window -> silently discard
```

**Deliverable**: Working Selective Repeat with configurable N, NAK support, and per-frame timers

---

### Phase 8: Testing & Metrics Collection

**Goal**: Run all protocols under various conditions and collect comparative data.

#### Test Matrix

| Protocol | Window N | Error Prob | Loss Prob | Metric Goal |
|----------|----------|-----------|-----------|-------------|
| SAW | 1 | 0.0 | 0.0 | Baseline |
| GBN | 4 | 0.0 | 0.0 | Baseline |
| SR | 4 | 0.0 | 0.0 | Baseline |
| SAW | 1 | 0.1 | 0.0 | Error test |
| GBN | 4 | 0.1 | 0.0 | Error test |
| SR | 4 | 0.1 | 0.0 | Error test |
| SAW | 1 | 0.3 | 0.0 | High error |
| GBN | 4 | 0.3 | 0.0 | High error |
| SR | 4 | 0.3 | 0.0 | High error |
| SAW | 1 | 0.5 | 0.0 | Max error |
| GBN | 4 | 0.5 | 0.0 | Max error |
| SR | 4 | 0.5 | 0.0 | Max error |
| SAW | 1 | 0.0 | 0.2 | Loss test |
| GBN | 4 | 0.0 | 0.2 | Loss test |
| SR | 4 | 0.0 | 0.2 | Loss test |

#### Metrics to Collect Per Run

- **Total transmission time** (seconds)
- **Number of frames sent** (including retransmissions)
- **Number of retransmissions**
- **Channel efficiency** = `(original frames x frame_size) / (total_sent x frame_size)`
- **Throughput** = `total_original_data_bytes / total_transmission_time`
- **Average RTT** per frame
- **Timeout adaptation log** — how timeout evolves over time

#### Correctness Verification

- Use a text file of known size (e.g., ~5000 bytes = ~108 frames at 46 bytes each)
- After transfer, **compare receiver's output file byte-for-byte with input**
- All three protocols must produce identical, correct output

---

## 6. Testing & Evaluation Plan

### Unit Tests

| Module | Test Cases |
|--------|-----------|
| `frame.py` | Build then parse (round trip), correct FCS computation, padding |
| `channel.py` | Loss rate matches configured probability, error injection detectable |
| `timer.py` | RTT updates converge, timeout expiry detection accurate |
| `sender.py` | Correct sequencing, window management, retransmission on timeout |
| `receiver.py` | Accept in-order, discard out-of-order (GBN), buffer out-of-order (SR) |

### Integration Tests

1. **Happy path**: Transfer file with zero errors -> output == input
2. **Error recovery**: Inject errors -> all data arrives correctly (more slowly)
3. **Timeout test**: Force long delays -> retransmission occurs correctly
4. **Window boundary**: Send exactly N, N-1, N+1 frames -> window management correct

### Comparative Analysis Plots

1. **Efficiency vs. Error Probability** for SAW, GBN, SR (line graph)
2. **Throughput vs. Window Size N** for GBN and SR at various error rates
3. **RTT over time** showing adaptive timeout convergence
4. **Retransmission count vs. Error Probability** comparing GBN vs. SR

---

## 7. Expected Results & Analysis

### Theoretical Efficiency Formulas

```
Let:
  a = T_prop / T_frame   (propagation-to-transmission ratio)
  p = error probability
  N = window size

Stop-and-Wait:
  eta_SAW = (1 - p) / (1 + 2a)

Go-Back-N:
  eta_GBN = (1 - p) / ((1 + 2a)(1 - p + N*p))

Selective Repeat:
  eta_SR = (1 - p) / (1 + 2a)   [when N >= 1+2a]
  eta_SR approx (1 - p)          [when N is optimal, large enough]
```

### Expected Trends

| Scenario | Expected Winner | Reason |
|----------|----------------|--------|
| No errors, small N | All similar | Window doesn't help if propagation delay is small |
| No errors, large propagation delay | SR = GBN >> SAW | Window keeps pipe full |
| High error rate (p=0.5), large N | SR >> GBN >> SAW | GBN's full-window retransmit is very wasteful |
| Low error rate, small N | All similar | Errors rare, window rarely triggered |

### Key Takeaway Insights

1. **Stop-and-Wait** is simple but wastes nearly all bandwidth when propagation delay is significant. Efficiency drops sharply with any errors because the sender sits idle during the entire RTT for every single frame.

2. **Go-Back-N** delivers dramatically higher throughput by keeping the channel busy. However, at high error rates, retransmitting entire windows is very wasteful — efficiency drops as `p` and `N` increase together.

3. **Selective Repeat** achieves the best efficiency at high error rates because only truly lost frames are retransmitted. Its complexity lies entirely in the receiver's buffering and sorting logic. The efficiency formula `(1-p)` shows it degrades gracefully with error rate.

4. **Adaptive Timeout** causes a "warm-up" period — early timeouts may trigger spurious retransmissions. As the RTT estimator converges to a stable value, retransmissions become more accurate and efficient.

---

*Document prepared for Data Communications & Networks Assignment 2*
*Last updated: 2026-08-25*
