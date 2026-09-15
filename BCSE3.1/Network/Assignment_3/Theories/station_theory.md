# Station Module Theory — `station.py`

> **File**: `station.py`  
> **Role**: Network host simulation  
> **Layer**: Data Link — MAC sublayer (station side)

---

## 1. What This Module Does

`station.py` models a **network station (host)** connected to the shared channel. Each station has a queue of frames to transmit, a state machine governing its behavior, and an implementation of the **Binary Exponential Backoff (BEB)** algorithm for collision recovery.

---

## 2. Station State Machine

```
                    ┌──────┐
           ┌───────│ IDLE │◀──────────────────────────┐
           │       └──┬───┘                           │
           │          │ has_data() & protocol says go  │
           │          ▼                                │
           │   ┌──────────────┐                       │
           │   │ TRANSMITTING │                       │
           │   └──────┬───────┘                       │
           │     ┌────┴────┐                          │
           │     │         │                          │
           │  success    collision                    │
           │     │         │                          │
           │     │    ┌────▼────┐   timer expires     │
           │     │    │ WAITING │──────────────────────┘
           │     │    └─────────┘
           │     │
           │     ▼
           │   ┌──────┐
           └──▶│ DONE │  (no more frames)
               └──────┘
```

---

## 3. Binary Exponential Backoff (BEB)

BEB is the collision recovery algorithm used in IEEE 802.3 Ethernet:

```
After collision k (1-indexed):
  1. Compute k' = min(k, max_k)        # max_k = 10 → cap at 1024 slots
  2. Choose random r ∈ [0, 2^k' - 1]
  3. Wait r × slot_time
  4. Retry transmission
  5. If k > max_retries (16) → give up, drop frame
```

### Why Exponential?

| After collision # | Wait range (slots) | Max wait |
|------------------:|-------------------:|---------:|
| 1 | [0, 1] | 1 |
| 2 | [0, 3] | 3 |
| 3 | [0, 7] | 7 |
| 5 | [0, 31] | 31 |
| 10 | [0, 1023] | 1023 |

The range **doubles** with each collision. This spreads contending stations over a wider time window, exponentially reducing the probability that they collide again.

### Why Cap at k=10?

Without a cap, the wait range would grow unboundedly (2^16 = 65,536 slots). The cap at k=10 ensures:
- Maximum wait is 1023 slots (practical for Ethernet)
- Stations don't wait indefinitely
- After 16 total retries, the frame is dropped (transmission failure)

---

## 4. Per-Station Metrics

Each station independently tracks:

| Metric | What it measures |
|--------|-----------------|
| `frames_sent` | Successfully delivered frames |
| `total_collisions` | Number of collisions this station experienced |
| `total_attempts` | Total transmission attempts (including retries) |
| `total_delay` | Cumulative delay from first attempt to success |
| `dropped_frames` | Frames abandoned after exceeding max retries |

### Delay Calculation

```
frame_delay = time_of_successful_delivery - time_of_first_attempt
```

This includes:
- All backoff waits due to collisions
- Re-sensing delays
- Actual transmission time
- Propagation delay effects

---

## 5. Key Methods

| Method | Purpose |
|--------|---------|
| `has_data()` | Check if queue is non-empty |
| `start_transmission(t)` | Begin transmitting head-of-queue frame |
| `complete_transmission(ok, t)` | Mark frame as delivered or failed |
| `handle_collision(t, slot)` | BEB: compute backoff, enter WAITING |
| `set_deferred(wait)` | Defer by p-persistent probability |
| `tick_backoff(slot)` | Decrement timer; WAITING → IDLE when done |
| `avg_delay()` | Average per-frame delay |
