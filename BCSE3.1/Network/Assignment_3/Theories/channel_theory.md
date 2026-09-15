# Channel Module Theory — `channel.py`

> **File**: `channel.py`  
> **Role**: Shared broadcast medium simulation  
> **Layer**: Physical layer abstraction

---

## 1. What This Module Does

`channel.py` models the **shared broadcast channel** that connects all stations in a CSMA network. It is the "wire" — a single collision domain where only one station can successfully transmit at a time.

The channel has three states:

| State | Meaning | Trigger |
|-------|---------|---------|
| `IDLE` | No station is transmitting | All transmissions finished or aborted |
| `BUSY` | Exactly one station is transmitting | A single `attempt_transmission()` call |
| `COLLISION` | Two or more stations are transmitting simultaneously | Multiple `attempt_transmission()` calls overlap |

---

## 2. Key Concepts Implemented

### State Machine

```
       ┌──────────────────────┐
       │                      │
  ┌────▼────┐           ┌─────────┐
  │  IDLE   │──1 tx──▶  │  BUSY   │
  └────▲────┘           └────┬────┘
       │                     │
       │            ┌────────┼────────┐
  all done          │ 2+ tx  │ 1 tx   │
       │            ▼        │ done   │
       │     ┌───────────┐   │
       └─────│ COLLISION  │◀──┘
             └───────────┘
```

### Propagation Delay

The `propagation_delay` parameter models the time it takes for a signal to travel from one end of the channel to the other. This creates a **vulnerability window** of `2 × τ` during which collisions can occur but not be immediately detected.

### Collision Detection

`check_collision()` simply checks if `len(active_transmitters) > 1`. In the real world this corresponds to:
- **Voltage comparison**: the received voltage doesn't match what was transmitted
- **Energy detection**: signal energy exceeds normal single-transmitter levels

### Jam Signal

When CSMA/CD detects a collision, it sends a **jam signal** — a special bit pattern that occupies the channel for `jam_duration` slots, ensuring all stations become aware of the collision.

### Statistics Tracking

The channel tracks per-slot counts of idle, busy, and collision slots. These are used to calculate:
- **Channel utilization** = `busy_slots / total_slots`
- **Collision rate** = `collision_slots / total_slots`

---

## 3. Thread Safety

All state-mutating methods are protected by a `threading.Lock()`. This allows the `Dashboard` module to safely read channel state from a different thread while the simulation loop is running.

---

## 4. Key Methods

| Method | Purpose |
|--------|---------|
| `sense(t)` | Carrier sensing — returns perceived channel state at time `t` |
| `attempt_transmission(sid, t, dur)` | Register a new transmitter |
| `check_collision()` | Check if 2+ stations are transmitting |
| `end_transmission(sid, t)` | Remove a station from active transmitters |
| `send_jam_signal(t, dur)` | Broadcast jam to notify all stations |
| `abort_all_transmissions(t)` | Abort all active tx (after collision) |
| `record_slot(t)` | Track channel state for statistics |
| `get_utilization(n)` | Calculate channel utilization |
