"""
timer.py
========
Per-frame timer and adaptive RTT/timeout management.

Implements:
  - Timer()   — start/stop a per-frame clock
  - Timeout() — update the timeout estimate using EWMA (TCP-style)

The algorithm mirrors RFC 6298 / Karn's algorithm:
    SRTT    = (1 - alpha) * SRTT + alpha * SampleRTT      alpha = 0.125
    RTTVAR  = (1 - beta)  * RTTVAR + beta * |SampleRTT - SRTT|  beta = 0.25
    Timeout = SRTT + 4 * RTTVAR

Usage:
    from timer import FrameTimer

    timer = FrameTimer(initial_timeout_ms=500)
    timer.start(seq_no=3)
    ...
    sample_rtt = timer.stop(seq_no=3)
    timer.update_timeout(sample_rtt)

    if timer.is_expired(seq_no=5):
        retransmit(5)
"""

import time
from typing import Optional


class FrameTimer:
    """
    Manages per-frame send-timestamps and computes an adaptive timeout.

    Attributes (read-only after construction)
    -----------------------------------------
    timeout_ms : float — current timeout interval in milliseconds
    est_rtt_ms : float — smoothed RTT estimate (SRTT) in milliseconds
    dev_rtt_ms : float — RTT variance estimate (RTTVAR) in milliseconds

    Parameters
    ----------
    initial_timeout_ms : float — starting timeout (ms); default 500 ms
    alpha              : float — SRTT smoothing factor;    RFC 6298 default 0.125
    beta               : float — RTTVAR smoothing factor;  RFC 6298 default 0.25
    min_timeout_ms     : float — floor for the timeout value (ms)
    max_timeout_ms     : float — ceiling for the timeout value (ms)
    """

    ALPHA_DEFAULT       = 0.125
    BETA_DEFAULT        = 0.25
    MIN_TIMEOUT_DEFAULT = 50.0    # ms — never time out faster than this
    MAX_TIMEOUT_DEFAULT = 10_000.0  # ms — never wait longer than 10 s

    def __init__(self,
                 initial_timeout_ms: float = 500.0,
                 alpha: float  = ALPHA_DEFAULT,
                 beta: float   = BETA_DEFAULT,
                 min_timeout_ms: float = MIN_TIMEOUT_DEFAULT,
                 max_timeout_ms: float = MAX_TIMEOUT_DEFAULT):

        self.timeout_ms     = initial_timeout_ms
        self.est_rtt_ms     = initial_timeout_ms / 4.0   # reasonable warm-up
        self.dev_rtt_ms     = 0.0
        self._alpha         = alpha
        self._beta          = beta
        self._min_timeout   = min_timeout_ms
        self._max_timeout   = max_timeout_ms

        # seq_no -> wall-clock send time (seconds, from time.monotonic)
        self._send_times: dict[int, float] = {}

        # History for analysis/logging
        self._rtt_samples: list[float] = []
        self._timeout_history: list[float] = []

    # ------------------------------------------------------------------
    # Timer() — start a frame timer
    # ------------------------------------------------------------------

    def start(self, seq_no: int) -> None:
        """
        Record the send timestamp for *seq_no*.

        Call this immediately after placing a frame on the channel.
        If *seq_no* already has a running timer (retransmit case), the
        old timestamp is overwritten with the current time.

        Parameters
        ----------
        seq_no : int — frame sequence number (0–255)
        """
        self._send_times[seq_no] = time.monotonic()

    # ------------------------------------------------------------------
    # stop() — stop a frame timer and return the RTT sample
    # ------------------------------------------------------------------

    def stop(self, seq_no: int) -> Optional[float]:
        """
        Record the ACK receipt time for *seq_no*, compute the RTT sample,
        remove the timer entry, and return the sample RTT in milliseconds.

        Returns None if no timer was running for *seq_no* (e.g. the ACK
        arrived after a spurious retransmit cleared the timer).

        Parameters
        ----------
        seq_no : int — frame sequence number

        Returns
        -------
        float | None — sample RTT in milliseconds, or None
        """
        send_time = self._send_times.pop(seq_no, None)
        if send_time is None:
            return None

        sample_rtt_ms = (time.monotonic() - send_time) * 1000.0
        self._rtt_samples.append(sample_rtt_ms)
        return sample_rtt_ms

    # ------------------------------------------------------------------
    # Timeout() — update the timeout estimate (RFC 6298 EWMA)
    # ------------------------------------------------------------------

    def update_timeout(self, sample_rtt_ms: float) -> float:
        """
        Recompute the timeout interval using the new RTT sample.

        Uses the RFC 6298 / Jacobson-Karels algorithm:
            SRTT   = (1 - α) * SRTT   + α * SampleRTT
            RTTVAR = (1 - β) * RTTVAR + β * |SampleRTT - SRTT|
            RTO    = SRTT + 4 * RTTVAR

        Parameters
        ----------
        sample_rtt_ms : float — measured RTT in milliseconds

        Returns
        -------
        float — new timeout value in milliseconds
        """
        # Update smoothed RTT
        self.est_rtt_ms = ((1 - self._alpha) * self.est_rtt_ms
                           + self._alpha * sample_rtt_ms)

        # Update RTT variance
        self.dev_rtt_ms = ((1 - self._beta) * self.dev_rtt_ms
                           + self._beta * abs(sample_rtt_ms - self.est_rtt_ms))

        # Compute new timeout and clamp to [min, max]
        new_timeout = self.est_rtt_ms + 4.0 * self.dev_rtt_ms
        self.timeout_ms = max(self._min_timeout,
                              min(new_timeout, self._max_timeout))

        self._timeout_history.append(self.timeout_ms)
        return self.timeout_ms

    # ------------------------------------------------------------------
    # is_expired() — check if a frame's timer has exceeded the timeout
    # ------------------------------------------------------------------

    def is_expired(self, seq_no: int) -> bool:
        """
        Return True if the timer for *seq_no* has exceeded *timeout_ms*.

        Returns False if no timer is running for *seq_no*.

        Parameters
        ----------
        seq_no : int — frame sequence number
        """
        send_time = self._send_times.get(seq_no)
        if send_time is None:
            return False
        elapsed_ms = (time.monotonic() - send_time) * 1000.0
        return elapsed_ms >= self.timeout_ms

    def elapsed_ms(self, seq_no: int) -> float:
        """
        Return how many milliseconds have passed since *seq_no* was started.
        Returns 0.0 if no timer is running.
        """
        send_time = self._send_times.get(seq_no)
        if send_time is None:
            return 0.0
        return (time.monotonic() - send_time) * 1000.0

    # ------------------------------------------------------------------
    # cancel() — cancel a timer without computing RTT (on deliberate discard)
    # ------------------------------------------------------------------

    def cancel(self, seq_no: int) -> None:
        """
        Remove the timer entry for *seq_no* without updating RTT.
        Use when a frame is deliberately abandoned (e.g. Go-Back-N reset).
        """
        self._send_times.pop(seq_no, None)

    def cancel_all(self) -> None:
        """Cancel all running timers (used on full window reset in GBN)."""
        self._send_times.clear()

    # ------------------------------------------------------------------
    # active_timers() — list of seq_nos with running timers
    # ------------------------------------------------------------------

    def active_timers(self) -> list[int]:
        """Return a sorted list of seq_nos that have active timers."""
        return sorted(self._send_times.keys())

    def expired_timers(self) -> list[int]:
        """Return a sorted list of seq_nos whose timers have expired."""
        return sorted(
            seq for seq in self._send_times
            if self.is_expired(seq)
        )

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def print_stats(self) -> None:
        """Print RTT and timeout statistics to stdout."""
        if not self._rtt_samples:
            print("[Timer] No RTT samples recorded yet.")
            return

        samples = self._rtt_samples
        avg_rtt  = sum(samples) / len(samples)
        min_rtt  = min(samples)
        max_rtt  = max(samples)

        print(f"\n[Timer] RTT Statistics ({len(samples)} samples):")
        print(f"  Min RTT     : {min_rtt:.2f} ms")
        print(f"  Max RTT     : {max_rtt:.2f} ms")
        print(f"  Average RTT : {avg_rtt:.2f} ms")
        print(f"  Smoothed RTT: {self.est_rtt_ms:.2f} ms  (SRTT)")
        print(f"  RTT Dev     : {self.dev_rtt_ms:.2f} ms  (RTTVAR)")
        print(f"  Current RTO : {self.timeout_ms:.2f} ms")

    @property
    def rtt_samples(self) -> list[float]:
        """All recorded RTT samples in ms (for plotting)."""
        return list(self._rtt_samples)

    @property
    def timeout_history(self) -> list[float]:
        """Sequence of timeout values after each update (for plotting)."""
        return list(self._timeout_history)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import random

    print("=" * 55)
    print("timer.py — self-test")
    print("=" * 55)

    t = FrameTimer(initial_timeout_ms=200.0)

    # Simulate 10 frame send/ACK cycles with random RTTs
    print("\nSimulating 10 frame round-trips with varying RTTs:")
    print(f"{'Seq':>4}  {'Sample RTT':>12}  {'SRTT':>10}  {'RTO':>10}")
    print("-" * 44)

    for seq in range(10):
        t.start(seq)
        # Simulate a random RTT between 20-150 ms
        simulated_rtt_ms = random.uniform(20, 150)
        time.sleep(simulated_rtt_ms / 1000.0)

        sample = t.stop(seq)
        t.update_timeout(sample)

        print(f"{seq:>4}  {sample:>10.1f} ms  {t.est_rtt_ms:>8.1f} ms  {t.timeout_ms:>8.1f} ms")

    t.print_stats()

    # Test expiry detection
    print("\n--- Expiry test ---")
    t2 = FrameTimer(initial_timeout_ms=50)
    t2.start(99)
    print(f"Immediately after start — expired: {t2.is_expired(99)}")
    time.sleep(0.06)   # 60 ms > 50 ms timeout
    print(f"After 60 ms sleep       — expired: {t2.is_expired(99)}")
    t2.cancel(99)
    print(f"After cancel            — expired: {t2.is_expired(99)}")

    print("\nSelf-test complete.")
