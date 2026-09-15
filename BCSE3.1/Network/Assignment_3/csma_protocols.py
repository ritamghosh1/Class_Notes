"""
csma_protocols.py
=================
Implementation of four CSMA (Carrier Sense Multiple Access) protocol variants.

Each protocol is a function that determines a station's action for a single
time slot, given the current channel state.  Actions are returned as Event
named-tuples for dashboard logging.

Protocols
---------
1. Non-Persistent CSMA  — if busy, wait random time, re-sense later
2. 1-Persistent CSMA    — if busy, keep sensing; transmit immediately when idle
3. p-Persistent CSMA    — if idle, transmit with probability p; else wait one slot
4. CSMA/CD              — 1-Persistent + detect collision during tx → abort + jam + BEB

Run standalone for self-tests:
    python3 csma_protocols.py
"""

import random
from dataclasses import dataclass
from typing import Optional

from channel import Channel, ChannelState
from station import Station, StationState


# ---------------------------------------------------------------------------
# Event types for dashboard logging
# ---------------------------------------------------------------------------

@dataclass
class Event:
    """Describes what happened during a protocol decision."""
    station_id:  int
    time:        float
    action:      str       # TRANSMIT, SENSE_BUSY, DEFER, BACKOFF, COLLISION, SUCCESS, DROP
    detail:      str = ""  # Extra info (e.g., "p=0.3, random=0.52 → deferred")

    def __str__(self) -> str:
        return f"[t={self.time:>8.1f}] Stn {self.station_id:>2d}: {self.action} {self.detail}"


# ---------------------------------------------------------------------------
# 1. Non-Persistent CSMA
# ---------------------------------------------------------------------------

def non_persistent_csma(station: Station,
                        channel: Channel,
                        current_time: float,
                        slot_time: float,
                        frame_duration: float) -> Optional[Event]:
    """
    Non-Persistent CSMA protocol decision for one slot.

    Algorithm:
        1. Sense channel.
        2. If IDLE  → transmit immediately.
        3. If BUSY  → wait a random time [1, 10] slots, then re-sense.

    Parameters
    ----------
    station        : Station  – the station making a decision
    channel        : Channel  – the shared channel
    current_time   : float    – current simulation time
    slot_time      : float    – slot duration
    frame_duration : float    – frame transmission time

    Returns
    -------
    Event or None
        Description of the action taken.
    """
    if station.state != StationState.IDLE or not station.has_data():
        return None

    ch_state = channel.sense(current_time)

    if ch_state == ChannelState.IDLE:
        # Channel free — transmit
        frame = station.start_transmission(current_time)
        if frame is not None:
            channel.attempt_transmission(station.id, current_time, frame_duration)
            return Event(station.id, current_time, "TRANSMIT",
                         f"frame={frame}")
    else:
        # Channel busy — wait random time, then re-sense
        wait_slots = random.randint(1, 10)
        wait_time = wait_slots * slot_time
        station.set_deferred(wait_time)
        return Event(station.id, current_time, "SENSE_BUSY",
                     f"non-persistent wait={wait_slots} slots")

    return None


# ---------------------------------------------------------------------------
# 2. 1-Persistent CSMA
# ---------------------------------------------------------------------------

def one_persistent_csma(station: Station,
                        channel: Channel,
                        current_time: float,
                        slot_time: float,
                        frame_duration: float) -> Optional[Event]:
    """
    1-Persistent CSMA protocol decision for one slot.

    Algorithm:
        1. Sense channel.
        2. If IDLE  → transmit immediately (with probability 1).
        3. If BUSY  → keep sensing (stay IDLE to try again next slot).

    The "keep sensing" behavior is modeled by simply returning without
    changing the station's state — it will re-enter this function on the
    next slot tick.
    """
    if station.state != StationState.IDLE or not station.has_data():
        return None

    ch_state = channel.sense(current_time)

    if ch_state == ChannelState.IDLE:
        frame = station.start_transmission(current_time)
        if frame is not None:
            channel.attempt_transmission(station.id, current_time, frame_duration)
            return Event(station.id, current_time, "TRANSMIT",
                         f"frame={frame} (1-persistent)")
    else:
        # Busy-wait: do nothing, try again next slot
        return Event(station.id, current_time, "SENSE_BUSY",
                     "1-persistent: will retry next slot")

    return None


# ---------------------------------------------------------------------------
# 3. p-Persistent CSMA
# ---------------------------------------------------------------------------

def p_persistent_csma(station: Station,
                      channel: Channel,
                      current_time: float,
                      slot_time: float,
                      frame_duration: float,
                      p: float = 0.3) -> Optional[Event]:
    """
    p-Persistent CSMA protocol decision for one slot.

    Algorithm:
        1. Sense channel.
        2. If IDLE:
           a. Generate random r ∈ [0, 1).
           b. If r < p → transmit.
           c. If r ≥ p → defer for one slot, then repeat.
        3. If BUSY → wait until idle (stay IDLE to try again next slot).

    Parameters
    ----------
    p : float
        Transmission probability when channel is sensed idle.
        p = 1.0 degenerates to 1-Persistent CSMA.
    """
    if station.state != StationState.IDLE or not station.has_data():
        return None

    ch_state = channel.sense(current_time)

    if ch_state == ChannelState.IDLE:
        r = random.random()
        if r < p:
            # Transmit with probability p
            frame = station.start_transmission(current_time)
            if frame is not None:
                channel.attempt_transmission(station.id, current_time, frame_duration)
                return Event(station.id, current_time, "TRANSMIT",
                             f"frame={frame} (p={p}, r={r:.3f} < p)")
        else:
            # Defer for one slot time
            station.set_deferred(slot_time)
            return Event(station.id, current_time, "DEFER",
                         f"p={p}, r={r:.3f} ≥ p → wait 1 slot")
    else:
        # Channel busy — wait (like 1-persistent, keep sensing)
        return Event(station.id, current_time, "SENSE_BUSY",
                     f"p-persistent: busy, retry next slot")

    return None


# ---------------------------------------------------------------------------
# 4. CSMA/CD (Collision Detection)
# ---------------------------------------------------------------------------

def csma_cd(station: Station,
            channel: Channel,
            current_time: float,
            slot_time: float,
            frame_duration: float) -> Optional[Event]:
    """
    CSMA/CD protocol decision for one slot.

    Algorithm:
        1. Sense channel (like 1-Persistent).
        2. If IDLE  → start transmitting.
        3. Collision detection happens in the simulation loop (not here),
           because we need to check *after all stations* have made their
           decisions for this slot.
        4. On collision → abort, send jam, BEB backoff.

    Note: The actual collision detection and abort are handled by the
    simulation engine after all stations have acted.  This function only
    handles the initial sense-and-transmit decision.
    """
    if station.state != StationState.IDLE or not station.has_data():
        return None

    ch_state = channel.sense(current_time)

    if ch_state == ChannelState.IDLE:
        frame = station.start_transmission(current_time)
        if frame is not None:
            channel.attempt_transmission(station.id, current_time, frame_duration)
            return Event(station.id, current_time, "TRANSMIT",
                         f"frame={frame} (CSMA/CD)")
    else:
        # Channel busy — keep sensing (1-Persistent behavior)
        return Event(station.id, current_time, "SENSE_BUSY",
                     "CSMA/CD: busy, retry next slot")

    return None


# ---------------------------------------------------------------------------
# Protocol dispatcher
# ---------------------------------------------------------------------------

PROTOCOLS = {
    "non_persistent": non_persistent_csma,
    "1_persistent":   one_persistent_csma,
    "p_persistent":   p_persistent_csma,
    "csma_cd":        csma_cd,
}

PROTOCOL_NAMES = {
    "non_persistent": "Non-Persistent CSMA",
    "1_persistent":   "1-Persistent CSMA",
    "p_persistent":   "p-Persistent CSMA",
    "csma_cd":        "CSMA/CD",
}


def get_protocol_func(protocol_name: str):
    """Return the protocol function for the given name."""
    if protocol_name not in PROTOCOLS:
        raise ValueError(f"Unknown protocol: {protocol_name}. "
                         f"Choose from: {list(PROTOCOLS.keys())}")
    return PROTOCOLS[protocol_name]


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  CSMA Protocols Module — Self-Test")
    print("=" * 60)

    random.seed(42)

    # --- Helper ---
    def fresh(n_frames=5):
        ch = Channel(propagation_delay=5)
        st = Station(station_id=0, frames_to_send=n_frames)
        return ch, st

    # Test 1: Non-Persistent — idle channel → transmit
    ch, st = fresh()
    ev = non_persistent_csma(st, ch, 0.0, 1.0, 10.0)
    assert ev is not None and ev.action == "TRANSMIT"
    print("[1] Non-Persistent: IDLE → TRANSMIT         ✓")

    # Test 2: Non-Persistent — busy channel → wait random
    ch2, st2 = fresh()
    ch2.attempt_transmission(99, 0.0, 10.0)  # make busy
    ev2 = non_persistent_csma(st2, ch2, 0.0, 1.0, 10.0)
    assert ev2 is not None and ev2.action == "SENSE_BUSY"
    assert st2.state == StationState.WAITING
    print("[2] Non-Persistent: BUSY → SENSE_BUSY+WAIT  ✓")

    # Test 3: 1-Persistent — idle → transmit
    ch3, st3 = fresh()
    ev3 = one_persistent_csma(st3, ch3, 0.0, 1.0, 10.0)
    assert ev3 is not None and ev3.action == "TRANSMIT"
    print("[3] 1-Persistent: IDLE → TRANSMIT            ✓")

    # Test 4: 1-Persistent — busy → sense_busy (no state change)
    ch4, st4 = fresh()
    ch4.attempt_transmission(99, 0.0, 10.0)
    ev4 = one_persistent_csma(st4, ch4, 0.0, 1.0, 10.0)
    assert ev4 is not None and ev4.action == "SENSE_BUSY"
    assert st4.state == StationState.IDLE  # stays idle to re-sense
    print("[4] 1-Persistent: BUSY → stays IDLE (sense) ✓")

    # Test 5: p-Persistent — idle, r < p → transmit
    random.seed(0)  # random.random() ≈ 0.844
    ch5, st5 = fresh()
    ev5 = p_persistent_csma(st5, ch5, 0.0, 1.0, 10.0, p=0.9)
    assert ev5 is not None and ev5.action == "TRANSMIT"
    print("[5] p-Persistent: IDLE, r<p → TRANSMIT      ✓")

    # Test 6: p-Persistent — idle, r ≥ p → defer
    random.seed(0)  # random.random() ≈ 0.844
    ch6, st6 = fresh()
    ev6 = p_persistent_csma(st6, ch6, 0.0, 1.0, 10.0, p=0.1)
    assert ev6 is not None and ev6.action == "DEFER"
    assert st6.state == StationState.WAITING
    print("[6] p-Persistent: IDLE, r≥p → DEFER         ✓")

    # Test 7: CSMA/CD — idle → transmit
    ch7, st7 = fresh()
    ev7 = csma_cd(st7, ch7, 0.0, 1.0, 10.0)
    assert ev7 is not None and ev7.action == "TRANSMIT"
    print("[7] CSMA/CD: IDLE → TRANSMIT                ✓")

    # Test 8: Protocol dispatcher
    func = get_protocol_func("csma_cd")
    assert func is csma_cd
    print("[8] Protocol dispatcher works               ✓")

    # Test 9: p=1.0 behaves like 1-persistent
    random.seed(99)
    ch9a, st9a = fresh()
    ch9b, st9b = fresh()
    ev9a = p_persistent_csma(st9a, ch9a, 0.0, 1.0, 10.0, p=1.0)
    random.seed(99)
    ev9b = one_persistent_csma(st9b, ch9b, 0.0, 1.0, 10.0)
    assert ev9a.action == ev9b.action == "TRANSMIT"
    print("[9] p=1.0 matches 1-persistent behavior     ✓")

    print()
    print("All CSMA protocol self-tests passed ✅")
    print("=" * 60)
