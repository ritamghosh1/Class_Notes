# CSMA Protocols Theory — `csma_protocols.py`

> **File**: `csma_protocols.py`  
> **Role**: Protocol decision logic for all four CSMA variants  
> **Layer**: Data Link — MAC sublayer (protocol logic)

---

## 1. What This Module Does

`csma_protocols.py` implements the **decision logic** for each of the four CSMA protocols. Each protocol is a function that receives a station, the channel, and the current time, and decides what the station should do in the current slot:
- **Transmit** (start sending)
- **Sense busy** (wait or re-sense)
- **Defer** (probabilistic delay in p-persistent)

Actions are returned as `Event` objects for dashboard logging.

---

## 2. Protocol Decision Trees

### Non-Persistent CSMA

```
Station has data?
  └─ YES → Sense channel
             ├─ IDLE  → TRANSMIT immediately
             └─ BUSY  → Wait random [1,10] slots → re-sense later
```

**Key insight**: The random wait when busy **reduces collision probability** because not all waiting stations rush to transmit when the channel becomes idle. However, it **increases delay** since the channel may be idle while stations are still in their random wait.

---

### 1-Persistent CSMA

```
Station has data?
  └─ YES → Sense channel
             ├─ IDLE  → TRANSMIT immediately (probability = 1)
             └─ BUSY  → Stay IDLE, try again next slot (busy-wait)
```

**Key insight**: The "1" in "1-persistent" means transmission probability = 1 when channel is sensed idle. This gives **lowest delay** under light load, but if multiple stations are waiting for a busy channel, they ALL transmit when it becomes idle → **guaranteed collision**.

---

### p-Persistent CSMA

```
Station has data?
  └─ YES → Sense channel
             ├─ IDLE  → Generate random r ∈ [0,1)
             │           ├─ r < p  → TRANSMIT
             │           └─ r ≥ p  → DEFER (wait 1 slot, try again)
             └─ BUSY  → Stay IDLE, try again next slot
```

**Key insight**: The probability `p` controls the trade-off:
- `p = 1.0` → degenerates to 1-Persistent (most aggressive)
- `p = 0.01` → very few collisions but high delay
- `p ≈ 1/N` → **optimal**: on average only 1 of N stations transmits

### Optimal p Derivation

If N stations are all waiting and channel becomes idle:
- Probability exactly 1 station transmits = `N × p × (1-p)^(N-1)`
- Maximized when `p = 1/N`

---

### CSMA/CD (Collision Detection)

```
Station has data?
  └─ YES → Sense channel (1-Persistent behavior)
             ├─ IDLE  → TRANSMIT + MONITOR for collision
             │           ├─ No collision during tx → SUCCESS
             │           └─ Collision detected     → ABORT + JAM + BEB backoff
             └─ BUSY  → Stay IDLE, try again next slot
```

**Key insight**: CSMA/CD is 1-Persistent CSMA **plus** the ability to detect collisions *during* transmission and abort immediately. This saves the wasted time of completing a collided frame:

| Aspect | Without CD | With CD (CSMA/CD) |
|--------|------------|-------------------|
| On collision | Complete full frame tx | Abort immediately |
| Wasted time | Full frame duration | Only time until detection |
| Recovery | Timeout-based | Immediate jam + BEB |

**Note**: In our simulation, collision detection happens in `simulation.py` (not in the protocol function), because we need to check *after all stations* have made their decisions for the slot.

---

## 3. Protocol Comparison Summary

| Feature | Non-Persistent | 1-Persistent | p-Persistent | CSMA/CD |
|---------|----------------|--------------|--------------|---------|
| On idle | Transmit | Transmit | Transmit w/ prob p | Transmit + monitor |
| On busy | Random wait | Busy-wait | Busy-wait | Busy-wait |
| Collision handling | Full tx + timeout | Full tx + timeout | Full tx + timeout | Abort + jam + BEB |
| Collision probability | Low | High | Medium (tunable) | High (but detected fast) |
| Delay (light load) | High | Low | Medium | Low |
| Throughput (heavy load) | Moderate | Low | Good (optimal p) | Best |

---

## 4. Event System

Each protocol function returns an `Event` dataclass:

```python
@dataclass
class Event:
    station_id:  int
    time:        float
    action:      str       # TRANSMIT, SENSE_BUSY, DEFER, COLLISION, SUCCESS, DROP
    detail:      str = ""  # Extra context for logging
```

This decouples protocol logic from visualization — the simulation engine and dashboard can independently consume these events.

---

## 5. Protocol Dispatcher

The `PROTOCOLS` dictionary maps string names to functions:

```python
PROTOCOLS = {
    "non_persistent": non_persistent_csma,
    "1_persistent":   one_persistent_csma,
    "p_persistent":   p_persistent_csma,
    "csma_cd":        csma_cd,
}
```

`get_protocol_func("csma_cd")` returns the corresponding function. This allows `simulation.py` and `benchmark.py` to dynamically select protocols by name.
