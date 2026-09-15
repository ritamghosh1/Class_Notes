# Computer Networks — Assignment 3
## Medium Access Control: CSMA Techniques with Collision Detection

> **Course**: CSE/PC/B/S/314 Computer Networks Lab
> **Topic**: Medium Access Control (MAC) — CSMA/CD Protocol
> **Prerequisites**: Basic networking concepts, socket programming

---

## Table of Contents

1. [What We Have To Do](#1-what-we-have-to-do)
2. [Core Concepts & Theory](#2-core-concepts--theory)
   - [The Problem: Shared Channel](#21-the-problem-shared-channel)
   - [What is MAC?](#22-what-is-mac)
   - [Channel Access Methods](#23-channel-access-methods)
   - [Carrier Sense (CS)](#24-carrier-sense-cs)
   - [Collision Detection (CD)](#25-collision-detection-cd)
   - [CSMA Variants](#26-csma-variants)
   - [Binary Exponential Backoff](#27-binary-exponential-backoff)
   - [Performance Metrics](#28-performance-metrics)
   - [Propagation Delay & Vulnerability Window](#29-propagation-delay--vulnerability-window)
3. [Things We Need to Know (Conceptual)](#3-things-we-need-to-know-conceptual)
4. [Approach & Strategy](#4-approach--strategy)
5. [Implementation Plan](#5-implementation-plan)
6. [Testing & Evaluation Plan](#6-testing--evaluation-plan)
7. [Expected Results & Analysis](#7-expected-results--analysis)
8. [Viva Questions & Answers](#8-viva-questions--answers)

---

## 1. What We Have To Do

This assignment asks us to simulate a **shared network channel** and multiple **network stations** that communicate using various **CSMA (Carrier Sense Multiple Access)** techniques. We need to implement and compare four MAC protocols:

### Protocol Summary

| Protocol | Behavior |
|----------|----------|
| **Non-Persistent CSMA** | Sense channel; if busy, wait random time and re-sense |
| **1-Persistent CSMA** | Sense channel; if busy, continuously sense until idle, then transmit with probability 1 |
| **p-Persistent CSMA** | Sense channel; if busy, wait; if idle, transmit with probability p |
| **CSMA/CD** | 1-Persistent CSMA + detect collisions during transmission and abort |

### What We Must Simulate

```
+----------------------------------+
|      SHARED CHANNEL              |
|  States: IDLE | BUSY | COLLISION |
+----------------------------------+
    ^          ^          ^
    |          |          |
+---+---+  +---+---+  +---+---+
|Station|  |Station|  |Station|
|  1    |  |  2    |  |  N    |
+-------+  +-------+  +-------+
```

### Required Analysis

1. **p-Persistent CSMA**: Plot collisions, delay, and throughput as functions of p (fixed N)
2. **All Schemes**: Plot the same metrics as functions of number of stations N
3. **Comparison**: Compare efficiency of all four schemes

---

## 2. Core Concepts & Theory

### 2.1 The Problem: Shared Channel

In early computer networks (like Ethernet), multiple computers share a single communication medium (coaxial cable). This creates a fundamental problem:

**If two or more computers transmit at the same time, their signals interfere → COLLISION**

```
Station A sends:  ──[Data A]──────────────────>
Station B sends:  ────────[Data B]────────────>
                             ↓
                        COLLISION!
                    (garbled signals)
```

The challenge is: **How do we decide who gets to transmit when?**

### 2.2 What is MAC?

**Medium Access Control (MAC)** is the sublayer of the Data Link Layer responsible for:

- Controlling how stations access the shared physical medium
- Preventing or resolving collisions
- Ensuring fair and efficient channel utilization

MAC protocols answer the question: **"When can a station transmit?"**

### 2.3 Channel Access Methods

There are three fundamental approaches to channel access:

#### 1. Contention-Based (Random Access)
- No central controller
- Stations compete for channel access
- Collisions possible but detected and resolved
- **Examples**: ALOHA, CSMA, CSMA/CD, CSMA/CA

#### 2. Controlled Access (Deterministic)
- Stations take turns in a predetermined order
- No collisions
- **Examples**: Token Ring, FDDI

#### 3. Channelization (Multiplexing)
- Channel divided by time, frequency, or code
- **Examples**: TDMA, FDMA, CDMA

**CSMA falls under Contention-Based protocols** — the most common approach in modern Ethernet and Wi-Fi.

### 2.4 Carrier Sense (CS)

**Carrier Sense** means: **Listen before you talk**

Before transmitting, a station checks if the channel is currently being used:

```
Station wants to send
         |
         v
+-------------------+
| Sense the Channel |
+-------------------+
         |
    +---------+
    |         |
    v         v
 IDLE      BUSY
    |         |
    v         v
 TRANSMIT   Wait/Backoff
```

**Implementation**:
```python
def carrier_sense(channel_state):
    """Check if channel is idle or busy"""
    if channel_state == "IDLE":
        return True   # Channel is free
    else:
        return False  # Channel is busy
```

**Key Point**: Carrier sense reduces collisions but doesn't eliminate them due to **propagation delay**.

### 2.5 Collision Detection (CD)

**Collision Detection** means: **Listen while you talk**

During transmission, the station continues monitoring the channel to detect if another station's signal interferes:

```
Station A transmits:
Time ──────────────────────────────────────────────>
    ┌─────────────────────────────────────────────┐
    │  Transmitting...                            │
    │  While also listening...                    │
    │  If energy > threshold → COLLISION!         │
    └─────────────────────────────────────────────┘
```

**How Collision is Detected**:
1. **Energy Detection**: Signal strength exceeds normal levels
2. **Voltage Comparison**: Transmitted signal ≠ Received signal
3. **Coding Violation**: Invalid signal patterns

**Implementation**:
```python
def detect_collision(transmitted_signal, received_signal):
    """Compare transmitted vs received signal"""
    if transmitted_signal != received_signal:
        return True  # Collision detected
    return False
```

### 2.6 CSMA Variants

#### Non-Persistent CSMA

**Behavior**:
1. Sense channel before transmitting
2. If IDLE → transmit immediately
3. If BUSY → **wait a random time**, then re-sense

```
Station A:  ──[Sense: BUSY]──[Wait random t1]──[Sense: IDLE]──[Transmit]──>
Station B:  ──[Sense: BUSY]──[Wait random t2]──[Sense: BUSY]──[Wait random t3]──>
```

**Advantages**:
- Simple to implement
- Better channel utilization than ALOHA

**Disadvantages**:
- Channel may remain idle even when stations have data (if all are waiting)
- High latency

```python
def non_persistent_csma(station, channel):
    while station.has_data():
        if sense_channel(channel) == "IDLE":
            transmit(station, channel)
        else:
            wait_random_time(station)  # Non-persistent wait
```

#### 1-Persistent CSMA

**Behavior**:
1. Sense channel before transmitting
2. If IDLE → transmit immediately (probability = 1)
3. If BUSY → **continuously sense** until idle, then transmit immediately

```
Station A:  ──[Sense: BUSY]──[Wait/Sense]──[Sense: IDLE]──[Transmit]──>
Station B:  ──[Sense: BUSY]──[Wait/Sense]──[Sense: IDLE]──[Transmit]──>
                                          ↑ COLLISION!
```

**Advantages**:
- Lower latency than Non-Persistent (transmits immediately when channel becomes free)

**Disadvantages**:
- **Higher collision probability** — multiple waiting stations all transmit simultaneously
- If two stations are both waiting, collision is guaranteed

```python
def one_persistent_csma(station, channel):
    while station.has_data():
        if sense_channel(channel) == "IDLE":
            transmit(station, channel)
        else:
            while sense_channel(channel) == "BUSY":
                pass  # Continuously sense (busy-wait)
            transmit(station, channel)  # Immediately transmit
```

#### p-Persistent CSMA

**Behavior**:
1. Sense channel before transmitting
2. If IDLE → transmit with probability **p**, and defer with probability **(1-p)**
3. If BUSY → wait until idle, then apply the same probability

```
Station A:  ──[Sense: IDLE]──[random() < p? YES]──[Transmit]──>
Station B:  ──[Sense: IDLE]──[random() < p? NO]──[Wait 1 slot]──[Sense: IDLE]──[random() < p? YES]──>
```

**Why Probability?**
- Reduces collision probability compared to 1-Persistent
- Multiple stations waiting won't all transmit at once
- Trade-off between delay and collision rate

```python
import random

def p_persistent_csma(station, channel, p=0.3):
    while station.has_data():
        if sense_channel(channel) == "IDLE":
            if random.random() < p:
                transmit(station, channel)
            else:
                wait_one_slot(station)  # Wait one slot time
        else:
            while sense_channel(channel) == "BUSY":
                pass  # Wait until idle
            # Then apply probability (same as idle case)
            if random.random() < p:
                transmit(station, channel)
            else:
                wait_one_slot(station)
```

**Key Parameter**: p (0 < p ≤ 1)
- p = 1 → becomes 1-Persistent CSMA
- p close to 0 → fewer collisions but higher delay
- p optimal ≈ 1/N (where N = number of stations)

#### CSMA/CD (Collision Detection)

**Behavior**:
1. Sense channel before transmitting
2. If IDLE → transmit and **simultaneously monitor** for collisions
3. If collision detected → **abort transmission immediately**
4. Send **jam signal** to notify all stations
5. Wait **backoff time** and retry

```
Station A:  ──[Sense: IDLE]──[Transmit]──[COLLISION! STOP]──[Backoff]──[Retry]──>
Station B:  ──[Sense: IDLE]──[Transmit]──[COLLISION! STOP]──[Backoff]──[Retry]──>
```

**CSMA/CD vs. 1-Persistent CSMA**:
- CSMA/CD **stops immediately** on collision (saves time)
- 1-Persistent CSMA **completes transmission** even if collision occurred (wastes bandwidth)

```python
def csma_cd(station, channel):
    while station.has_data():
        if sense_channel(channel) == "IDLE":
            start_transmitting(station, channel)
            # Monitor while transmitting
            while not transmission_complete(station):
                if detect_collision(station, channel):
                    abort_transmission(station)
                    send_jam_signal(channel)
                    backoff_time = calculate_backoff(station)
                    wait(backoff_time)
                    break
        else:
            wait_random_time(station)  # Like Non-Persistent
```

### 2.7 Binary Exponential Backoff (BEB)

When a collision occurs, stations must wait before retrying. The **Binary Exponential Backoff** algorithm determines how long to wait:

**Algorithm**:
```
After collision k:
  1. Choose random wait time from [0, 2^k - 1] slots
  2. Wait that many slot times
  3. Retry transmission
  4. If collision again, increment k (up to max = 10)
  5. If k > 10, give up (transmission failed)
```

**Example**:
```
Station A collides (k=0):
  Wait random from [0, 0] → wait 0 slots (transmit immediately)

Station A collides again (k=1):
  Wait random from [0, 1] → wait 0 or 1 slot

Station A collides again (k=2):
  Wait random from [0, 3] → wait 0, 1, 2, or 3 slots

Station A collides again (k=3):
  Wait random from [0, 7] → wait 0 to 7 slots

...exponential growth up to k=10 → wait 0 to 1023 slots
```

**Why "Exponential"?**
- Wait time range doubles with each collision
- Reduces collision probability exponentially
- Allows stations to spread out over time

**Implementation**:
```python
import random

class BackoffCalculator:
    def __init__(self, slot_time=0.0512):  # 51.2 microseconds for Ethernet
        self.slot_time = slot_time
        self.max_retries = 16
        self.max_k = 10  # 2^10 = 1024 max slots
    
    def calculate_backoff(self, collision_count):
        """Calculate backoff time in seconds"""
        if collision_count > self.max_retries:
            return -1  # Failed, give up
        
        k = min(collision_count, self.max_k)
        max_slots = (2 ** k) - 1
        random_slots = random.randint(0, max_slots)
        return random_slots * self.slot_time
```

### 2.8 Performance Metrics

#### 1. Number of Collisions

**Definition**: Count of transmission attempts where two or more stations' signals overlapped.

```
Collisions = Total transmission attempts - Successful transmissions
```

**Why it matters**: Each collision wastes channel time and increases delay.

#### 2. Average Transmission Delay

**Definition**: Average time from when a station begins attempting to transmit until successful delivery.

```
Transmission Delay = (Time of successful delivery) - (Time of first attempt)
```

**Includes**:
- Sensing delay
- Backoff wait time(s)
- Transmission time
- Propagation delay

#### 3. Channel Throughput

**Definition**: Rate of successful data delivery over the channel.

```
Throughput = (Total successful data bits) / (Total time)
Efficiency = Throughput / Channel capacity
```

**Normalized Throughput**:
```
S = (Successful frames × Frame_size) / (Total_simulation_time × Channel_rate)
```

### 2.9 Propagation Delay & Vulnerability Window

**Propagation Delay (τ)**: Time for a signal to travel from one end of the channel to the other.

```
τ = Distance / Speed of signal

For Ethernet (10 Mbps, 100m cable):
τ ≈ 0.5 microseconds
```

**Vulnerability Window**: The time period during which a collision can occur but not be immediately detected.

```
Vulnerability Window = 2 × τ

Why 2τ?
─────────────────────────────────────────────
t=0     Station A starts transmitting
t=τ-ε   Station B senses channel (still IDLE at B's location)
t=τ     Station A's signal reaches B
t=τ     Station B starts transmitting → COLLISION!
t=2τ    Station A detects collision (B's signal reaches A)
─────────────────────────────────────────────

The vulnerability window is [0, 2τ]
```

**Implication**: Even with carrier sense, collisions are inevitable due to propagation delay.

---

## 3. Things We Need to Know (Conceptual)

Before starting implementation, solidify these concepts:

### Fundamental Concepts
- [ ] What is a shared channel and why collisions occur
- [ ] What MAC (Medium Access Control) means
- [ ] Difference between contention-based and controlled access
- [ ] What carrier sensing is and why it's not perfect

### CSMA Protocol Details
- [ ] How Non-Persistent CSMA works (wait random, re-sense)
- [ ] How 1-Persistent CSMA works (busy-wait, transmit immediately)
- [ ] How p-Persistent CSMA works (probabilistic transmission)
- [ ] How CSMA/CD works (detect collision, abort, backoff)
- [ ] The role of probability p in p-Persistent CSMA

### Backoff & Collision Resolution
- [ ] How Binary Exponential Backoff works
- [ ] Why backoff time doubles with each collision
- [ ] Maximum retry limit and its purpose

### Performance Analysis
- [ ] How to calculate throughput: (successful data) / (total time)
- [ ] How to count collisions accurately
- [ ] How to measure transmission delay
- [ ] The relationship between p and collision rate
- [ ] The relationship between N (stations) and performance

### Simulation Concepts
- [ ] How to model time in discrete-event simulation
- [ ] How to implement carrier sensing
- [ ] How to detect and handle collisions
- [ ] How to track channel state (IDLE, BUSY, COLLISION)

---

## 4. Approach & Strategy

### Overall Architecture

```
+------------------------------------------+
|           SIMULATION ENGINE              |
+------------------------------------------+
|                                          |
|  +------------------------------------+  |
|  |        SHARED CHANNEL              |  |
|  |  State: IDLE | BUSY | COLLISION    |  |
|  +------------------------------------+  |
|         ^       ^       ^       ^        |
|         |       |       |       |        |
|     +---+---+ +---+---+ +---+---+ +---+ |
|     |Stn 1  | |Stn 2  | |Stn 3  | |Stn N|
|     |       | |       | |       | |     |
|     |Sense()| |Sense()| |Sense()| |Sense|
|     |Send() | |Send() | |Send() | |Send |
|     +-------+ +-------+ +-------+ +-----+
|                                          |
+------------------------------------------+
|           METRICS COLLECTOR              |
|  - Collision counter per station         |
|  - Transmission delay tracker            |
|  - Throughput calculator                 |
+------------------------------------------+
```

### Key Design Decisions

#### 1. Channel State Machine

```
                    ┌──────────────────┐
                    │                  │
          ┌────────▼────────┐        │
          │      IDLE       │        │
          └────────┬────────┘        │
                   │                  │
          Station starts tx           │
                   │                  │
          ┌────────▼────────┐        │
          │      BUSY       │        │
          └────────┬────────┘        │
                   │                  │
      ┌────────────┼────────────┐    │
      │            │            │    │
  Normal tx    Collision     Tx complete
  completes    detected           │
      │            │            │
      │            ▼            │
      │     ┌─────────────┐    │
      │     │  COLLISION   │    │
      │     └──────┬──────┘    │
      │            │            │
      │     Jam signal sent     │
      │            │            │
      └────────┬───┴────────────┘
               │
          Backoff timer expires
               │
               ▼
          (return to IDLE)
```

#### 2. Station Class Design

```python
class Station:
    def __init__(self, station_id, channel):
        self.id = station_id
        self.channel = channel
        self.state = "IDLE"  # IDLE, WAITING, TRANSMITTING
        self.collision_count = 0
        self.data_queue = []  # Frames to send
        self.backoff_k = 0    # Current backoff exponent
```

#### 3. Channel Class Design

```python
class Channel:
    def __init__(self, propagation_delay):
        self.state = "IDLE"
        self.propagation_delay = propagation_delay
        self.transmitting_stations = []
        
    def sense(self):
        """Returns IDLE or BUSY"""
        return self.state
    
    def start_transmission(self, station):
        """Station begins transmitting"""
        if self.state == "IDLE":
            self.state = "BUSY"
            self.transmitting_stations.append(station)
            return True
        return False  # Channel busy, can't transmit
    
    def detect_collision(self):
        """Check if multiple stations are transmitting"""
        return len(self.transmitting_stations) > 1
    
    def end_transmission(self, station):
        """Station finishes transmitting"""
        self.transmitting_stations.remove(station)
        if not self.transmitting_stations:
            self.state = "IDLE"
```

#### 4. Simulation Loop

```python
def run_simulation(protocol, N_stations, simulation_time):
    channel = Channel(propagation_delay=tau)
    stations = [Station(i, channel) for i in range(N_stations)]
    
    # Initialize each station with data to send
    for station in stations:
        station.data_queue = generate_frames(frames_per_station)
    
    time = 0
    while time < simulation_time:
        for station in stations:
            if station.state == "IDLE" and station.has_data():
                # Try to transmit based on protocol
                if protocol == "non_persistent":
                    non_persistent_csma(station, channel)
                elif protocol == "1_persistent":
                    one_persistent_csma(station, channel)
                elif protocol == "p_persistent":
                    p_persistent_csma(station, channel, p)
                elif protocol == "csma_cd":
                    csma_cd(station, channel)
            
            elif station.state == "WAITING":
                # Check if backoff timer expired
                if station.backoff_timer <= 0:
                    station.state = "IDLE"
        
        # Advance time by one slot
        time += slot_time
        
        # Update backoff timers
        for station in stations:
            if station.state == "WAITING":
                station.backoff_timer -= slot_time
        
        # Check for collisions
        if channel.detect_collision():
            handle_collision(stations, channel)
    
    return collect_metrics(stations, channel)
```

### Comparison Strategy

| Factor | Non-Persistent | 1-Persistent | p-Persistent | CSMA/CD |
|--------|----------------|--------------|--------------|---------|
| Sensing | Before tx | Before tx | Before + during | Before + during |
| If busy | Wait random | Busy-wait | Busy-wait | Busy-wait |
| If idle | Transmit | Transmit (p=1) | Transmit (p) | Transmit |
| Collision handling | Timeout + retry | Complete tx + retry | Complete tx + retry | Abort + jam + retry |
| Complexity | Low | Low | Medium | High |
| Best for | Low traffic | Low-medium traffic | Tunable | Ethernet |

---

## 5. Implementation Plan

### Phase 1: Channel Module

**Goal**: Implement the shared channel with state management.

#### 1.1 — Channel States

```python
from enum import Enum

class ChannelState(Enum):
    IDLE = 0
    BUSY = 1
    COLLISION = 2
```

#### 1.2 — Channel Class

```python
class Channel:
    def __init__(self, propagation_delay=0.001):
        self.state = ChannelState.IDLE
        self.prop_delay = propagation_delay
        self.active_transmitters = []
        self.busy_until = 0  # Time when channel becomes idle
        self.total_busy_time = 0
        self.total_collision_time = 0
    
    def sense(self, current_time):
        """Check if channel is idle or busy"""
        if current_time < self.busy_until:
            return ChannelState.BUSY
        if self.state == ChannelState.COLLISION:
            return ChannelState.COLLISION
        return ChannelState.IDLE
    
    def attempt_transmission(self, station_id, current_time, frame_duration):
        """Try to start transmitting"""
        if self.sense(current_time) == ChannelState.IDLE:
            self.active_transmitters.append(station_id)
            self.busy_until = current_time + frame_duration
            self.state = ChannelState.BUSY
            return True
        return False
    
    def check_collision(self):
        """Check if collision occurred"""
        if len(self.active_transmitters) > 1:
            self.state = ChannelState.COLLISION
            return True
        return False
    
    def end_transmission(self, station_id):
        """Remove station from active transmitters"""
        if station_id in self.active_transmitters:
            self.active_transmitters.remove(station_id)
        if not self.active_transmitters:
            self.state = ChannelState.IDLE
```

#### 1.3 — Unit Tests for Channel

```python
def test_channel_idle():
    ch = Channel()
    assert ch.sense(0) == ChannelState.IDLE

def test_channel_busy():
    ch = Channel()
    ch.attempt_transmission(1, 0, 1.0)
    assert ch.sense(0.5) == ChannelState.BUSY

def test_channel_collision():
    ch = Channel()
    ch.attempt_transmission(1, 0, 1.0)
    ch.attempt_transmission(2, 0, 1.0)
    assert ch.check_collision() == True
```

**Deliverable**: `channel.py` with Channel class and state management

---

### Phase 2: Station Module

**Goal**: Implement stations that follow CSMA strategies.

#### 2.1 — Station Class

```python
import random

class Station:
    def __init__(self, station_id):
        self.id = station_id
        self.state = "IDLE"
        self.data_queue = []
        self.backoff_k = 0
        self.backoff_timer = 0
        self.collision_count = 0
        self.frames_sent = 0
        self.total_delay = 0
    
    def has_data(self):
        return len(self.data_queue) > 0
    
    def generate_data(self, num_frames, frame_size):
        """Generate frames to transmit"""
        self.data_queue = [f"Frame_{i}" for i in range(num_frames)]
    
    def start_transmission(self):
        """Begin transmitting a frame"""
        if self.data_queue:
            self.state = "TRANSMITTING"
            return self.data_queue[0]
        return None
    
    def complete_transmission(self, success):
        """Finish transmitting current frame"""
        if success:
            self.data_queue.pop(0)
            self.frames_sent += 1
            self.backoff_k = 0  # Reset backoff on success
        self.state = "IDLE"
    
    def handle_collision(self):
        """Handle collision with backoff"""
        self.collision_count += 1
        self.state = "WAITING"
        self.backoff_timer = self.calculate_backoff()
    
    def calculate_backoff(self):
        """Binary Exponential Backoff"""
        max_slots = (2 ** min(self.backoff_k, 10)) - 1
        random_slots = random.randint(0, max_slots)
        self.backoff_k += 1
        return random_slots * SLOT_TIME
```

**Deliverable**: `station.py` with Station class

---

### Phase 3: CSMA Protocol Implementations

**Goal**: Implement all four CSMA variants.

#### 3.1 — Non-Persistent CSMA

```python
def non_persistent_csma(station, channel, current_time):
    """Non-Persistent CSMA implementation"""
    if station.state != "IDLE":
        return
    
    channel_state = channel.sense(current_time)
    
    if channel_state == ChannelState.IDLE:
        # Channel is free, transmit
        frame = station.start_transmission()
        if frame:
            channel.attempt_transmission(station.id, current_time, FRAME_DURATION)
    
    else:
        # Channel busy, wait random time and re-sense later
        wait_time = random.uniform(1, 10) * SLOT_TIME
        station.backoff_timer = wait_time
        station.state = "WAITING"
```

#### 3.2 — 1-Persistent CSMA

```python
def one_persistent_csma(station, channel, current_time):
    """1-Persistent CSMA implementation"""
    if station.state != "IDLE":
        return
    
    channel_state = channel.sense(current_time)
    
    if channel_state == ChannelState.IDLE:
        # Channel free, transmit immediately (p=1)
        frame = station.start_transmission()
        if frame:
            channel.attempt_transmission(station.id, current_time, FRAME_DURATION)
    
    else:
        # Channel busy, continuously sense until idle
        while channel.sense(current_time) == ChannelState.BUSY:
            current_time += SLOT_TIME  # Busy-wait
        
        # Channel just became idle, transmit immediately
        frame = station.start_transmission()
        if frame:
            channel.attempt_transmission(station.id, current_time, FRAME_DURATION)
```

#### 3.3 — p-Persistent CSMA

```python
def p_persistent_csma(station, channel, current_time, p=0.3):
    """p-Persistent CSMA implementation"""
    if station.state != "IDLE":
        return
    
    channel_state = channel.sense(current_time)
    
    if channel_state == ChannelState.IDLE:
        # Channel free, transmit with probability p
        if random.random() < p:
            frame = station.start_transmission()
            if frame:
                channel.attempt_transmission(station.id, current_time, FRAME_DURATION)
        else:
            # Defer, wait one slot and try again
            station.backoff_timer = SLOT_TIME
            station.state = "WAITING"
    
    else:
        # Channel busy, wait until idle, then apply probability
        while channel.sense(current_time) == ChannelState.BUSY:
            current_time += SLOT_TIME
        
        # Now channel is idle, apply probability
        if random.random() < p:
            frame = station.start_transmission()
            if frame:
                channel.attempt_transmission(station.id, current_time, FRAME_DURATION)
        else:
            station.backoff_timer = SLOT_TIME
            station.state = "WAITING"
```

#### 3.4 — CSMA/CD

```python
def csma_cd(station, channel, current_time):
    """CSMA/CD implementation"""
    if station.state != "IDLE":
        return
    
    channel_state = channel.sense(current_time)
    
    if channel_state == ChannelState.IDLE:
        # Channel free, start transmitting
        frame = station.start_transmission()
        if frame:
            channel.attempt_transmission(station.id, current_time, FRAME_DURATION)
            
            # Monitor for collision during transmission
            for t in range(FRAME_DURATION):
                current_time += SLOT_TIME
                if channel.check_collision():
                    # Collision detected! Abort immediately
                    station.complete_transmission(success=False)
                    channel.end_transmission(station.id)
                    
                    # Send jam signal
                    send_jam_signal(channel)
                    
                    # Backoff and retry
                    station.handle_collision()
                    return
            
            # Transmission completed successfully
            station.complete_transmission(success=True)
            channel.end_transmission(station.id)
    
    else:
        # Channel busy, wait random time (like Non-Persistent)
        wait_time = random.uniform(1, 10) * SLOT_TIME
        station.backoff_timer = wait_time
        station.state = "WAITING"
```

**Deliverable**: `csma_protocols.py` with all four protocol implementations

---

### Phase 4: Simulation Engine

**Goal**: Create the main simulation loop.

#### 4.1 — Simulation Parameters

```python
SIMULATION_CONFIG = {
    "num_stations": [2, 4, 6, 8, 10],       # N values to test
    "p_values": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    "simulation_time": 1000,                  # seconds
    "slot_time": 0.0512,                      # 51.2 microseconds (Ethernet)
    "frame_duration": 0.512,                  # 512 microseconds
    "propagation_delay": 0.001,               # 1 microsecond
    "frames_per_station": 100,
    "num_runs": 10,                           # For averaging
}
```

#### 4.2 — Main Simulation Loop

```python
def run_simulation(protocol, N, p=None, config=SIMULATION_CONFIG):
    """Run a single simulation"""
    # Initialize
    channel = Channel(config["propagation_delay"])
    stations = [Station(i) for i in range(N)]
    
    for station in stations:
        station.generate_data(config["frames_per_station"], FRAME_SIZE)
    
    # Statistics
    total_collisions = 0
    total_frames_sent = 0
    total_delay = 0
    start_time = time.time()
    
    # Simulation loop
    current_time = 0
    while current_time < config["simulation_time"]:
        for station in stations:
            # Update backoff timers
            if station.state == "WAITING":
                station.backoff_timer -= config["slot_time"]
                if station.backoff_timer <= 0:
                    station.state = "IDLE"
            
            # Try to transmit
            if station.state == "IDLE" and station.has_data():
                if protocol == "non_persistent":
                    non_persistent_csma(station, channel, current_time)
                elif protocol == "1_persistent":
                    one_persistent_csma(station, channel, current_time)
                elif protocol == "p_persistent":
                    p_persistent_csma(station, channel, current_time, p)
                elif protocol == "csma_cd":
                    csma_cd(station, channel, current_time)
        
        # Check for collisions
        if channel.check_collision():
            total_collisions += 1
            # Handle collision for all transmitting stations
            for station_id in channel.active_transmitters:
                stations[station_id].handle_collision()
            channel.active_transmitters.clear()
            channel.state = ChannelState.IDLE
        
        # Advance time
        current_time += config["slot_time"]
    
    # Calculate metrics
    elapsed_time = time.time() - start_time
    total_frames = sum(s.frames_sent for s in stations)
    
    metrics = {
        "collisions": total_collisions,
        "frames_sent": total_frames,
        "avg_delay": total_delay / max(total_frames, 1),
        "throughput": (total_frames * FRAME_SIZE) / elapsed_time,
    }
    
    return metrics
```

**Deliverable**: `simulation.py` with main simulation engine

---

### Phase 5: Metrics Collection & Plotting

**Goal**: Collect data and generate plots.

#### 5.1 — Metrics Collector

```python
def collect_metrics(protocol, N_values, p_values, runs=10):
    """Collect metrics for different parameters"""
    results = {
        "non_persistent": {"collisions": [], "delay": [], "throughput": []},
        "1_persistent": {"collisions": [], "delay": [], "throughput": []},
        "p_persistent": {"collisions": [], "delay": [], "throughput": []},
        "csma_cd": {"collisions": [], "delay": [], "throughput": []},
    }
    
    # Test for different N
    for N in N_values:
        for protocol in ["non_persistent", "1_persistent", "p_persistent", "csma_cd"]:
            avg_metrics = {"collisions": 0, "delay": 0, "throughput": 0}
            for _ in range(runs):
                metrics = run_simulation(protocol, N)
                avg_metrics["collisions"] += metrics["collisions"]
                avg_metrics["delay"] += metrics["avg_delay"]
                avg_metrics["throughput"] += metrics["throughput"]
            
            # Average over runs
            results[protocol]["collisions"].append(avg_metrics["collisions"] / runs)
            results[protocol]["delay"].append(avg_metrics["delay"] / runs)
            results[protocol]["throughput"].append(avg_metrics["throughput"] / runs)
    
    return results
```

#### 5.2 — Plot Generation

```python
import matplotlib.pyplot as plt

def plot_results(results, N_values):
    """Generate comparison plots"""
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    protocols = ["non_persistent", "1_persistent", "p_persistent", "csma_cd"]
    colors = ["blue", "red", "green", "orange"]
    
    # Plot 1: Collisions vs N
    for protocol, color in zip(protocols, colors):
        axes[0, 0].plot(N_values, results[protocol]["collisions"], 
                       marker='o', label=protocol, color=color)
    axes[0, 0].set_xlabel("Number of Stations (N)")
    axes[0, 0].set_ylabel("Number of Collisions")
    axes[0, 0].set_title("Collisions vs N")
    axes[0, 0].legend()
    axes[0, 0].grid(True)
    
    # Plot 2: Delay vs N
    for protocol, color in zip(protocols, colors):
        axes[0, 1].plot(N_values, results[protocol]["delay"],
                       marker='s', label=protocol, color=color)
    axes[0, 1].set_xlabel("Number of Stations (N)")
    axes[0, 1].set_ylabel("Avg Transmission Delay (s)")
    axes[0, 1].set_title("Delay vs N")
    axes[0, 1].legend()
    axes[0, 1].grid(True)
    
    # Plot 3: Throughput vs N
    for protocol, color in zip(protocols, colors):
        axes[0, 2].plot(N_values, results[protocol]["throughput"],
                       marker='^', label=protocol, color=color)
    axes[0, 2].set_xlabel("Number of Stations (N)")
    axes[0, 2].set_ylabel("Throughput (bits/s)")
    axes[0, 2].set_title("Throughput vs N")
    axes[0, 2].legend()
    axes[0, 2].grid(True)
    
    plt.tight_layout()
    plt.savefig("csma_comparison.png", dpi=150)
    plt.show()
```

**Deliverable**: `plot_results.py` with plotting functions

---

## 6. Testing & Evaluation Plan

### Test Cases

| Test Case | Parameters | Expected Result |
|-----------|------------|-----------------|
| Single station | N=1, any protocol | Zero collisions, max throughput |
| Two stations | N=2, p=1.0 | Some collisions due to simultaneous start |
| Many stations | N=10, any protocol | High collision rate |
| p-persistent sweep | N=5, p=0.1 to 1.0 | Optimal p around 0.2-0.3 |
| Protocol comparison | N=5, all protocols | CSMA/CD best, Non-Persistent worst |

### Verification Methods

1. **Correctness**: Single station should have zero collisions
2. **Consistency**: More stations → more collisions (monotonic increase)
3. **Stability**: Run multiple times, average should be stable
4. **Comparison**: CSMA/CD should outperform others at high load

### Performance Analysis

#### Expected Trends

| Metric | As N increases | As p increases |
|--------|----------------|----------------|
| Collisions | Increase | Increase |
| Delay | Increase | Decrease then increase |
| Throughput | Decrease | Increase then decrease |

#### Theoretical Limits

```
Maximum Throughput (Normalized):
- Non-Persistent CSMA:  S_max ≈ 0.81 (at offered load G=0.5)
- 1-Persistent CSMA:    S_max ≈ 0.55 (at offered load G=1.0)
- p-Persistent CSMA:    S_max ≈ 0.84 (at optimal p)
- CSMA/CD:              S_max ≈ 0.93 (Ethernet)
```

---

## 7. Expected Results & Analysis

### Theoretical Formulas

#### Throughput Formulas

```
Let:
  G = offered load (average number of transmission attempts per frame time)
  p = persistence probability
  N = number of stations
  a = propagation_delay / transmission_time

Non-Persistent CSMA:
  S = G * e^(-a*G) / (G * (1+2a) + e^(-a*G))

1-Persistent CSMA:
  S = G * (1 + G + a*G) * e^(-G*(1+a)) / (G*(1+a) - (1-a)*e^(-a*G) + (1+a^2))

p-Persistent CSMA:
  S = G * e^(-a*G) / (G*(1+2a) + e^(-a*G))
  
  where G = N * p * (1-p)^(N-1) for offered load approximation
```

### Expected Observations

1. **Non-Persistent CSMA**:
   - Lowest collision rate (waits random time)
   - Highest delay (always waits even when channel is free)
   - Lowest throughput under heavy load

2. **1-Persistent CSMA**:
   - Highest collision rate (multiple stations wait and transmit simultaneously)
   - Lowest delay under light load (transmits immediately when idle)
   - Moderate throughput

3. **p-Persistent CSMA**:
   - Tunable trade-off between collision and delay
   - Optimal p depends on N: p_optimal ≈ 1/N
   - Best throughput among pure CSMA protocols

4. **CSMA/CD**:
   - Best throughput (aborts early on collision)
   - Moderate complexity
   - Standard for Ethernet (IEEE 802.3)

### Impact Analysis

| Scenario | Best Protocol | Reason |
|----------|---------------|--------|
| Low traffic (N < 3) | 1-Persistent | Minimal collisions, lowest delay |
| Medium traffic (3 < N < 10) | p-Persistent | Balanced collision/delay trade-off |
| High traffic (N > 10) | CSMA/CD | Early collision detection saves time |
| Real-time applications | Non-Persistent | Predictable delay (no starvation) |
| High throughput needed | CSMA/CD | Highest channel utilization |

---

## 8. Viva Questions & Answers

### Basic Concepts

**Q1: What is the difference between CSMA/CD and CSMA/CA?**

**A**: 
- **CSMA/CD** (Collision Detection): Used in wired Ethernet. Detects collisions during transmission and aborts immediately.
- **CSMA/CA** (Collision Avoidance): Used in Wi-Fi (802.11). Avoids collisions by waiting random backoff before transmitting, even if channel is idle.

**Q2: Why can't we eliminate collisions completely with CSMA?**

**A**: Due to **propagation delay**. When Station A starts transmitting, Station B (at the other end of the cable) may not detect A's signal immediately. If B also starts transmitting before A's signal reaches B, collision occurs.

**Q3: What is the vulnerability window in CSMA?**

**A**: The time period [0, 2τ] during which a collision can occur but not be immediately detected. τ is the propagation delay. During this window, two stations may sense the channel as idle and transmit simultaneously.

**Q4: What is the advantage of CSMA/CD over 1-Persistent CSMA?**

**A**: CSMA/CD **aborts immediately** when collision is detected and sends a jam signal. 1-Persistent CSMA **completes the entire transmission** even if collision occurred, wasting channel time. This makes CSMA/CD much more efficient.

**Q5: How does Binary Exponential Backoff work?**

**A**: After the k-th collision:
1. Choose random wait time from [0, 2^k - 1] slot times
2. Wait that duration
3. Retry transmission
4. If collision again, increment k (up to k=10)
5. If k > 10, give up (transmission failed)

The wait range doubles exponentially, reducing collision probability over time.

### Protocol-Specific Questions

**Q6: When would you use Non-Persistent CSMA over 1-Persistent?**

**A**: Non-Persistent is better when:
- Channel load is high (reduces collisions)
- Predictable delay is important (no starvation)
- Channel is expensive (long propagation delay)

1-Persistent is better when:
- Channel load is low
- Low latency is critical
- Channel is cheap (short propagation delay)

**Q7: What is the optimal value of p in p-Persistent CSMA?**

**A**: The optimal p depends on the number of stations N:
- For N stations, optimal p ≈ 1/N
- For example, with N=5 stations, optimal p ≈ 0.2

This ensures that on average, only one station transmits when the channel becomes idle.

**Q8: How does p-Persistent CSMA handle multiple stations waiting?**

**A**: When multiple stations are waiting and channel becomes idle:
1. Each station generates random number r ∈ [0, 1]
2. If r < p, station transmits
3. If r ≥ p, station waits one slot and tries again

This probabilistic approach ensures not all stations transmit simultaneously, reducing collisions.

**Q9: What happens if two stations choose the same backoff time in CSMA/CD?**

**A**: They will collide again. This is why Binary Exponential Backoff uses **exponentially increasing ranges** — after multiple collisions, the probability of choosing the same backoff time decreases exponentially.

**Q10: Why is the minimum frame size 64 bytes in Ethernet?**

**A**: To ensure collision detection works:
- Frame transmission time must be ≥ 2 × propagation delay
- For 10 Mbps Ethernet with 2500m cable:
  - Propagation delay ≈ 25 μs
  - Minimum frame time ≈ 50 μs
  - Minimum frame size ≈ 500 bits ≈ 64 bytes

### Performance Analysis

**Q11: How does increasing N affect throughput?**

**A**: Throughput **decreases** as N increases because:
- More stations → more contention
- Higher collision probability
- More time wasted on backoffs
- Channel utilization drops

**Q12: Why does 1-Persistent CSMA have the worst performance at high load?**

**A**: At high load, many stations are waiting. When channel becomes idle:
- All waiting stations transmit simultaneously (p=1)
- Collision is guaranteed
- Wasted channel time increases
- Effective throughput drops significantly

**Q13: How do you measure throughput in simulation?**

**A**: 
```
Throughput = (Total successful data bits) / (Total simulation time)
           = (Number of successful frames × Frame size in bits) / Simulation time

Normalized Throughput = Throughput / Channel capacity
```

**Q14: What is the relationship between offered load and throughput?**

**A**: 
- **Low load**: Throughput increases linearly with load
- **Medium load**: Throughput peaks at optimal point
- **High load**: Throughput decreases due to collisions

The curve is called the **throughput-load curve** and typically peaks at:
- Non-Persistent: G ≈ 0.5
- 1-Persistent: G ≈ 1.0
- p-Persistent: G depends on p

**Q15: How does propagation delay affect performance?**

**A**: Higher propagation delay:
- Increases vulnerability window
- More collisions occur
- Lower throughput
- Longer backoff times needed

Formula: Throughput ∝ 1 / (1 + 2a), where a = τ / T_frame

### Implementation Questions

**Q16: How do you simulate time in discrete-event simulation?**

**A**: 
```python
current_time = 0
slot_time = 0.0512  # 51.2 microseconds

while current_time < simulation_time:
    # Process all events at current_time
    for station in stations:
        process_station(station, current_time)
    
    # Advance time by one slot
    current_time += slot_time
```

**Q17: How do you implement carrier sensing?**

**A**: Check channel state variable:
```python
def carrier_sense(channel):
    if channel.state == ChannelState.IDLE:
        return True  # Channel is free
    else:
        return False  # Channel is busy
```

**Q18: How do you detect collision in simulation?**

**A**: Check if multiple stations are transmitting simultaneously:
```python
def detect_collision(channel):
    return len(channel.active_transmitters) > 1
```

**Q19: What data structure would you use for the backoff timer?**

**A**: Use a priority queue (min-heap) for efficient timer management:
```python
import heapq

class BackoffTimer:
    def __init__(self):
        self.timers = []  # (expire_time, station_id)
    
    def add(self, expire_time, station_id):
        heapq.heappush(self.timers, (expire_time, station_id))
    
    def get_expired(self, current_time):
        expired = []
        while self.timers and self.timers[0][0] <= current_time:
            expired.append(heapq.heappop(self.timers))
        return expired
```

**Q20: How do you handle simultaneous events in simulation?**

**A**: Process all events at the same timestamp before advancing time:
```python
while current_time < simulation_time:
    # Get all events at current_time
    events = get_events_at(current_time)
    
    # Process in order: sensing → transmission → collision detection
    events.sort(key=lambda e: e.priority)
    
    for event in events:
        process_event(event)
    
    # Advance time
    current_time += slot_time
```

### Advanced Questions

**Q21: What is the hidden terminal problem?**

**A**: In wireless networks, Station A may sense channel as idle (can't hear Station B transmitting), while Station B is transmitting to Station C. If A also transmits, collision occurs at C. This is called the **hidden terminal problem** and is solved by CSMA/CA with RTS/CTS mechanism.

**Q22: How does CSMA/CD differ from Token Ring?**

**A**: 
| Feature | CSMA/CD | Token Ring |
|---------|---------|------------|
| Access method | Contention | Controlled |
| Collisions | Yes | No |
| Fairness | Statistical | Guaranteed |
| Complexity | Low | High |
| Best for | Bursty traffic | Real-time traffic |

**Q23: What is the capture effect in CSMA?**

**A**: After a collision, one station may successfully transmit while the other backs off. If the first station continues transmitting, the second station may keep backing off indefinitely, "capturing" the channel. This is unfair but can improve throughput.

**Q24: How does IEEE 802.3 (Ethernet) implement CSMA/CD?**

**A**: 
- Uses 1-Persistent CSMA/CD
- Minimum frame size: 64 bytes (512 bits)
- Maximum cable length: 2500 meters
- Backoff algorithm: Binary Exponential Backoff
- Jam signal: 32 bits of 1s
- Slot time: 51.2 microseconds

**Q25: What are the limitations of CSMA/CD?**

**A**: 
1. Not effective in wireless (can't detect collisions while transmitting)
2. Performance degrades with network size (propagation delay increases)
3. Not suitable for real-time applications (unbounded delay)
4. Efficiency drops at high load (>80% utilization)

---

## Quick Reference: Key Formulas

```
Throughput (S) = Successful_data_bits / Total_time

Offered Load (G) = Average_attempts_per_frame_time

Efficiency (η) = Throughput / Channel_capacity

Collision Probability = 1 - e^(-2*G)  [for pure ALOHA]
                      = 1 - e^(-G)    [for slotted ALOHA]

Backoff Time = Random(0, 2^k - 1) × Slot_Time

Optimal p ≈ 1/N (for p-Persistent CSMA)

Vulnerability Window = 2 × Propagation_Delay

Minimum_Frame_Size = 2 × Propagation_Delay × Channel_Rate
```

---

*Document prepared for Computer Networks Lab - Assignment 3*
*CSMA Techniques with Collision Detection*
*Last updated: 2026-09-08*
