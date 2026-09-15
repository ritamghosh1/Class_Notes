"""
station.py
==========
Network station model for CSMA simulation.

Each Station represents a host connected to the shared broadcast channel.
Stations maintain their own data queues, state machines, and per-station
metrics (collisions, delay, frames sent).  The Binary Exponential Backoff
(BEB) algorithm is implemented here.

Usage:
    s = Station(station_id=0, frames_to_send=100)
    s.start_transmission(current_time)
    s.complete_transmission(success=True, current_time=15.0)
    s.handle_collision(current_time=5.0, slot_time=1.0)

Run standalone for self-tests:
    python3 station.py
"""

from enum import Enum
import random


# ---------------------------------------------------------------------------
# Station state enum
# ---------------------------------------------------------------------------

class StationState(Enum):
    """Station finite-state machine states."""
    IDLE          = 0   # Has data, ready to sense/transmit
    SENSING       = 1   # Currently sensing the channel
    TRANSMITTING  = 2   # Frame is being transmitted
    WAITING       = 3   # Backing off after collision / deferred by p-persistent
    DONE          = 4   # No more data to send


# ---------------------------------------------------------------------------
# Station class
# ---------------------------------------------------------------------------

class Station:
    """
    Represents a single network station connected to the shared channel.

    Parameters
    ----------
    station_id    : int   – unique identifier (0 to N-1)
    frames_to_send: int   – number of frames in the data queue
    max_retries   : int   – maximum number of retransmission attempts (default 16)
    max_k         : int   – backoff exponent cap (default 10, giving 2^10=1024 slots max)
    """

    def __init__(self,
                 station_id: int,
                 frames_to_send: int = 100,
                 max_retries: int = 16,
                 max_k: int = 10):
        self.id              = station_id
        self.state           = StationState.IDLE
        self.max_retries     = max_retries
        self.max_k           = max_k

        # Data queue
        self.data_queue      = list(range(frames_to_send))  # frame indices
        self.current_frame   = None

        # Backoff state
        self.backoff_k       = 0       # current collision count for BEB
        self.backoff_timer   = 0.0     # remaining backoff time (in slot times)

        # Transmission timing
        self.tx_start_time   = 0.0     # when current frame attempt started
        self.first_attempt_time = 0.0  # when we first tried this frame

        # ---- Per-station metrics ----
        self.metrics = {
            "frames_sent":       0,     # successfully transmitted frames
            "total_collisions":  0,     # total collisions experienced
            "total_attempts":    0,     # total transmission attempts
            "total_delay":       0.0,   # cumulative delay across all frames
            "dropped_frames":    0,     # frames abandoned after max_retries
        }

    # ------------------------------------------------------------------
    # Data queue management
    # ------------------------------------------------------------------

    def has_data(self) -> bool:
        """Return True if the station still has frames to send."""
        return len(self.data_queue) > 0

    def peek_frame(self) -> int | None:
        """Return the next frame index without removing it."""
        if self.data_queue:
            return self.data_queue[0]
        return None

    # ------------------------------------------------------------------
    # Transmission lifecycle
    # ------------------------------------------------------------------

    def start_transmission(self, current_time: float) -> int | None:
        """
        Begin transmitting the head-of-queue frame.

        Records the attempt start time and transitions to TRANSMITTING.

        Returns
        -------
        int | None
            Frame index being transmitted, or None if no data.
        """
        if not self.data_queue:
            self.state = StationState.DONE
            return None

        self.current_frame = self.data_queue[0]
        self.state = StationState.TRANSMITTING
        self.tx_start_time = current_time
        self.metrics["total_attempts"] += 1

        # Record the *first* attempt time for this frame (for delay calc)
        if self.backoff_k == 0:
            self.first_attempt_time = current_time

        return self.current_frame

    def complete_transmission(self, success: bool, current_time: float) -> None:
        """
        Complete the current transmission attempt.

        Parameters
        ----------
        success      : bool  – True if frame was delivered without collision
        current_time : float – simulation time at completion
        """
        if success:
            # Frame delivered successfully
            if self.data_queue:
                self.data_queue.pop(0)
            self.metrics["frames_sent"] += 1
            self.metrics["total_delay"] += (current_time - self.first_attempt_time)
            self.backoff_k = 0  # reset backoff on success
            self.current_frame = None

            if self.data_queue:
                self.state = StationState.IDLE
            else:
                self.state = StationState.DONE
        else:
            # Transmission failed (collision) — state managed by handle_collision
            self.state = StationState.IDLE

    # ------------------------------------------------------------------
    # Collision handling & Binary Exponential Backoff
    # ------------------------------------------------------------------

    def handle_collision(self, current_time: float, slot_time: float) -> float:
        """
        Handle a collision: increment backoff counter and compute wait time.

        Uses Binary Exponential Backoff (BEB):
            Wait time = random(0, 2^min(k, max_k) - 1) × slot_time

        Parameters
        ----------
        current_time : float – when collision was detected
        slot_time    : float – slot duration for backoff calculation

        Returns
        -------
        float
            Backoff wait time in simulation time units.
            Returns -1 if max retries exceeded (frame dropped).
        """
        self.metrics["total_collisions"] += 1
        self.backoff_k += 1

        if self.backoff_k > self.max_retries:
            # Give up on this frame
            if self.data_queue:
                self.data_queue.pop(0)
            self.metrics["dropped_frames"] += 1
            self.backoff_k = 0
            self.current_frame = None
            self.state = StationState.IDLE if self.data_queue else StationState.DONE
            return -1.0

        # BEB: choose random slots in [0, 2^k - 1]
        k = min(self.backoff_k, self.max_k)
        max_slots = (2 ** k) - 1
        random_slots = random.randint(0, max_slots)
        wait_time = random_slots * slot_time

        self.backoff_timer = wait_time
        self.state = StationState.WAITING
        return wait_time

    def set_deferred(self, wait_time: float) -> None:
        """
        Defer transmission (used by p-persistent when random > p).

        Parameters
        ----------
        wait_time : float – time to wait before re-sensing
        """
        self.backoff_timer = wait_time
        self.state = StationState.WAITING

    # ------------------------------------------------------------------
    # Timer management
    # ------------------------------------------------------------------

    def tick_backoff(self, slot_time: float) -> bool:
        """
        Decrement the backoff timer by one slot.

        Returns
        -------
        bool
            True if backoff timer has expired (station transitions to IDLE).
        """
        if self.state != StationState.WAITING:
            return False

        self.backoff_timer -= slot_time
        if self.backoff_timer <= 0:
            self.backoff_timer = 0
            self.state = StationState.IDLE
            return True
        return False

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def avg_delay(self) -> float:
        """Average per-frame delay (0 if no frames sent)."""
        sent = self.metrics["frames_sent"]
        return self.metrics["total_delay"] / sent if sent > 0 else 0.0

    def __repr__(self) -> str:
        return (f"Station(id={self.id}, state={self.state.name}, "
                f"queue={len(self.data_queue)}, "
                f"collisions={self.metrics['total_collisions']})")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  Station Module — Self-Test")
    print("=" * 60)

    # Test 1: Station initializes correctly
    s = Station(station_id=0, frames_to_send=5)
    assert s.state == StationState.IDLE
    assert s.has_data() is True
    assert len(s.data_queue) == 5
    print("[1] Station initializes (IDLE, 5 frames)   ✓")

    # Test 2: Start transmission
    frame = s.start_transmission(current_time=0.0)
    assert frame == 0
    assert s.state == StationState.TRANSMITTING
    assert s.metrics["total_attempts"] == 1
    print("[2] Start transmission → TRANSMITTING      ✓")

    # Test 3: Successful completion
    s.complete_transmission(success=True, current_time=10.0)
    assert s.state == StationState.IDLE
    assert s.metrics["frames_sent"] == 1
    assert len(s.data_queue) == 4
    assert s.metrics["total_delay"] == 10.0
    print("[3] Successful completion → IDLE, 4 left    ✓")

    # Test 4: Collision handling with BEB
    random.seed(42)
    s2 = Station(station_id=1, frames_to_send=3)
    s2.start_transmission(0.0)
    wait = s2.handle_collision(current_time=2.0, slot_time=1.0)
    assert s2.state == StationState.WAITING
    assert s2.backoff_k == 1
    assert wait >= 0  # random(0, 0) or random(0, 1)
    print(f"[4] Collision → WAITING, backoff={wait:.0f} slots ✓")

    # Test 5: BEB escalation
    s3 = Station(station_id=2, frames_to_send=1)
    for k in range(1, 6):
        s3.state = StationState.IDLE
        s3.start_transmission(0.0)
        s3.handle_collision(0.0, slot_time=1.0)
        max_possible = (2 ** min(s3.backoff_k - 1, s3.max_k)) - 1  # before increment
    assert s3.backoff_k == 5  # after 5 collisions
    print("[5] BEB escalation (k=5 after 5 collisions) ✓")

    # Test 6: Max retries → frame dropped
    s4 = Station(station_id=3, frames_to_send=2, max_retries=3)
    for _ in range(4):  # exceed max_retries
        s4.state = StationState.IDLE
        s4.start_transmission(0.0)
        result = s4.handle_collision(0.0, slot_time=1.0)
    assert result == -1.0
    assert s4.metrics["dropped_frames"] == 1
    print("[6] Max retries exceeded → frame dropped     ✓")

    # Test 7: Backoff timer tick
    s5 = Station(station_id=4, frames_to_send=1)
    s5.set_deferred(wait_time=3.0)
    assert s5.state == StationState.WAITING
    s5.tick_backoff(1.0)  # 3→2
    assert s5.state == StationState.WAITING
    s5.tick_backoff(1.0)  # 2→1
    assert s5.state == StationState.WAITING
    s5.tick_backoff(1.0)  # 1→0 → IDLE
    assert s5.state == StationState.IDLE
    print("[7] Backoff timer ticks down → IDLE          ✓")

    # Test 8: Empty queue → DONE
    s6 = Station(station_id=5, frames_to_send=1)
    s6.start_transmission(0.0)
    s6.complete_transmission(success=True, current_time=5.0)
    assert s6.state == StationState.DONE
    assert s6.has_data() is False
    print("[8] Last frame sent → DONE                  ✓")

    # Test 9: avg_delay calculation
    s7 = Station(station_id=6, frames_to_send=2)
    s7.start_transmission(0.0)
    s7.complete_transmission(True, 10.0)
    s7.start_transmission(10.0)
    s7.complete_transmission(True, 25.0)
    assert s7.avg_delay() == (10.0 + 15.0) / 2.0
    print(f"[9] Avg delay = {s7.avg_delay():.1f}               ✓")

    print()
    print("All station self-tests passed ✅")
    print("=" * 60)
