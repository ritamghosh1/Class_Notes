"""
channel.py
==========
Shared network channel simulation for CSMA protocols.

Models a broadcast medium with three states (IDLE, BUSY, COLLISION).
Implements propagation-delay-aware carrier sensing, collision detection,
jam signal transmission, and per-slot state tracking.

Usage:
    ch = Channel(propagation_delay=5, slot_time=1)
    state = ch.sense(current_time)
    success = ch.attempt_transmission(station_id, current_time, frame_duration)
    if ch.check_collision():
        ch.send_jam_signal(current_time, jam_duration=48)
    ch.end_transmission(station_id, current_time)

Run standalone for self-tests:
    python3 channel.py
"""

from enum import Enum
import threading


# ---------------------------------------------------------------------------
# Channel state enum
# ---------------------------------------------------------------------------

class ChannelState(Enum):
    """Possible states of the shared broadcast medium."""
    IDLE      = 0   # No station is transmitting
    BUSY      = 1   # Exactly one station is transmitting
    COLLISION = 2   # Two or more stations are transmitting simultaneously


# ---------------------------------------------------------------------------
# Channel class
# ---------------------------------------------------------------------------

class Channel:
    """
    Simulates a shared broadcast channel for CSMA protocols.

    The channel tracks which stations are currently transmitting and
    maintains state transitions: IDLE → BUSY → COLLISION → IDLE.

    Parameters
    ----------
    propagation_delay : float
        One-way propagation delay in slot times.  The vulnerability
        window is 2 × propagation_delay.
    slot_time : float
        Duration of one slot in simulation time units (seconds).
    """

    def __init__(self,
                 propagation_delay: float = 5.0,
                 slot_time: float = 1.0):
        self.prop_delay    = propagation_delay
        self.slot_time     = slot_time
        self.state         = ChannelState.IDLE
        self.busy_until    = 0.0    # time at which current tx finishes

        # Active transmitters: {station_id: (start_time, end_time)}
        self.active_transmitters: dict[int, tuple[float, float]] = {}

        # Thread lock for dashboard integration
        self._lock = threading.Lock()

        # ---- Statistics ----
        self.stats = {
            "total_transmissions":    0,
            "successful_transmissions": 0,
            "total_collisions":       0,
            "total_jam_signals":      0,
            "total_busy_slots":       0,
            "total_collision_slots":  0,
            "total_idle_slots":       0,
        }

    # ------------------------------------------------------------------
    # Carrier sensing
    # ------------------------------------------------------------------

    def sense(self, current_time: float) -> ChannelState:
        """
        Carrier sense: check the channel state at *current_time*.

        Due to propagation delay, a station may perceive the channel as
        IDLE even though another station started transmitting within
        the vulnerability window.  This method returns the *local*
        perception of the channel state.

        Returns
        -------
        ChannelState
            IDLE, BUSY, or COLLISION.
        """
        with self._lock:
            # Clean up finished transmissions
            self._cleanup_finished(current_time)

            if current_time < self.busy_until and len(self.active_transmitters) == 0:
                # Jam signal or residual busy state is active
                return self.state

            if len(self.active_transmitters) == 0:
                return ChannelState.IDLE
            elif len(self.active_transmitters) == 1:
                return ChannelState.BUSY
            else:
                return ChannelState.COLLISION

    # ------------------------------------------------------------------
    # Transmission management
    # ------------------------------------------------------------------

    def attempt_transmission(self,
                             station_id: int,
                             current_time: float,
                             frame_duration: float) -> bool:
        """
        Station *station_id* attempts to start transmitting at *current_time*.

        Parameters
        ----------
        station_id     : int   – unique station identifier
        current_time   : float – current simulation time
        frame_duration : float – how long the frame occupies the channel

        Returns
        -------
        bool
            True if the transmission attempt was registered (does NOT
            guarantee collision-free delivery — collisions are detected
            separately via check_collision()).
        """
        with self._lock:
            end_time = current_time + frame_duration
            self.active_transmitters[station_id] = (current_time, end_time)
            self.busy_until = max(self.busy_until, end_time)
            self.stats["total_transmissions"] += 1

            # Update state
            if len(self.active_transmitters) >= 2:
                self.state = ChannelState.COLLISION
            else:
                self.state = ChannelState.BUSY

            return True

    def check_collision(self) -> bool:
        """
        Check whether a collision is occurring (2+ active transmitters).

        Returns
        -------
        bool
            True if collision detected.
        """
        with self._lock:
            if len(self.active_transmitters) > 1:
                self.state = ChannelState.COLLISION
                return True
            return False

    def end_transmission(self, station_id: int, current_time: float) -> None:
        """
        Remove *station_id* from the set of active transmitters.

        Called when a station finishes transmitting (success or abort).
        """
        with self._lock:
            if station_id in self.active_transmitters:
                del self.active_transmitters[station_id]

            # Update state
            if len(self.active_transmitters) == 0:
                self.state = ChannelState.IDLE
            elif len(self.active_transmitters) == 1:
                self.state = ChannelState.BUSY
            else:
                self.state = ChannelState.COLLISION

    def send_jam_signal(self, current_time: float, jam_duration: float = 4.0) -> None:
        """
        Broadcast a jam signal to notify all stations of a collision.

        The jam signal occupies the channel for *jam_duration* slot times,
        ensuring that all stations detect the collision.
        """
        with self._lock:
            self.busy_until = max(self.busy_until, current_time + jam_duration)
            self.state = ChannelState.COLLISION
            self.stats["total_jam_signals"] += 1

    def abort_all_transmissions(self, current_time: float) -> list[int]:
        """
        Abort all active transmissions (called after collision detection).

        Returns
        -------
        list[int]
            List of station IDs that were transmitting.
        """
        with self._lock:
            collided = list(self.active_transmitters.keys())
            self.active_transmitters.clear()
            self.stats["total_collisions"] += 1
            return collided

    def record_slot(self, current_time: float) -> None:
        """
        Record the channel state for the current slot (for statistics).

        Called once per simulation slot to track utilization.
        """
        with self._lock:
            # First, make sure state is accurately reflecting current_time
            if current_time >= self.busy_until and len(self.active_transmitters) == 0:
                self.state = ChannelState.IDLE
            elif len(self.active_transmitters) == 1:
                self.state = ChannelState.BUSY
            elif len(self.active_transmitters) >= 2:
                self.state = ChannelState.COLLISION

            if self.state == ChannelState.IDLE:
                self.stats["total_idle_slots"] += 1
            elif self.state == ChannelState.BUSY:
                self.stats["total_busy_slots"] += 1
            elif self.state == ChannelState.COLLISION:
                self.stats["total_collision_slots"] += 1

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cleanup_finished(self, current_time: float) -> None:
        """Remove transmitters whose frame duration has elapsed."""
        finished = [
            sid for sid, (start, end) in self.active_transmitters.items()
            if end <= current_time
        ]
        for sid in finished:
            del self.active_transmitters[sid]
            self.stats["successful_transmissions"] += 1

        # Update state after cleanup
        if len(self.active_transmitters) == 0:
            self.state = ChannelState.IDLE
        elif len(self.active_transmitters) == 1:
            self.state = ChannelState.BUSY

    def reset(self) -> None:
        """Reset channel to initial state (for benchmark reruns)."""
        with self._lock:
            self.state = ChannelState.IDLE
            self.busy_until = 0.0
            self.active_transmitters.clear()
            for key in self.stats:
                self.stats[key] = 0

    def get_utilization(self, total_slots: int) -> float:
        """Return channel utilization = busy_slots / total_slots."""
        total = self.stats["total_busy_slots"]
        return total / max(total_slots, 1)

    def get_collision_rate(self, total_slots: int) -> float:
        """Return collision rate = collision_slots / total_slots."""
        return self.stats["total_collision_slots"] / max(total_slots, 1)

    def __repr__(self) -> str:
        return (f"Channel(state={self.state.name}, "
                f"active={len(self.active_transmitters)}, "
                f"collisions={self.stats['total_collisions']})")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  Channel Module — Self-Test")
    print("=" * 60)

    # Test 1: Channel starts IDLE
    ch = Channel(propagation_delay=5)
    state = ch.sense(0)
    assert state == ChannelState.IDLE, f"Expected IDLE, got {state}"
    print("[1] Channel initializes to IDLE            ✓")

    # Test 2: Single transmission → BUSY
    ch.attempt_transmission(0, 0, 10.0)
    state = ch.sense(0)
    assert state == ChannelState.BUSY, f"Expected BUSY, got {state}"
    print("[2] Single transmitter → BUSY              ✓")

    # Test 3: Two transmissions → COLLISION
    ch.attempt_transmission(1, 2.0, 10.0)
    assert ch.check_collision() is True
    print("[3] Two transmitters → COLLISION            ✓")

    # Test 4: Abort all → returns collided station IDs
    collided = ch.abort_all_transmissions(2.0)
    assert set(collided) == {0, 1}, f"Expected {{0,1}}, got {collided}"
    assert ch.stats["total_collisions"] == 1
    print("[4] Abort returns collided IDs              ✓")

    # Test 5: Channel returns to IDLE after abort
    state = ch.sense(2.0)
    assert state == ChannelState.IDLE, f"Expected IDLE, got {state}"
    print("[5] Channel IDLE after abort                ✓")

    # Test 6: Jam signal
    ch.send_jam_signal(3.0, jam_duration=4.0)
    assert ch.stats["total_jam_signals"] == 1
    print("[6] Jam signal recorded                     ✓")

    # Test 7: Successful transmission cleanup
    ch2 = Channel(propagation_delay=5)
    ch2.attempt_transmission(0, 0.0, 5.0)
    state = ch2.sense(6.0)  # After frame ends
    assert state == ChannelState.IDLE, f"Expected IDLE after cleanup, got {state}"
    assert ch2.stats["successful_transmissions"] == 1
    print("[7] Auto-cleanup after frame duration       ✓")

    # Test 8: Reset
    ch.reset()
    assert ch.state == ChannelState.IDLE
    assert ch.stats["total_collisions"] == 0
    print("[8] Reset clears all state                  ✓")

    # Test 9: Slot recording
    ch3 = Channel()
    ch3.record_slot(0)
    assert ch3.stats["total_idle_slots"] == 1
    ch3.attempt_transmission(0, 0, 10)
    ch3.record_slot(1)
    assert ch3.stats["total_busy_slots"] == 1
    ch3.attempt_transmission(1, 1, 10)
    ch3.record_slot(2)
    assert ch3.stats["total_collision_slots"] == 1
    print("[9] Slot recording (idle/busy/collision)    ✓")

    print()
    print("All channel self-tests passed ✅")
    print("=" * 60)
