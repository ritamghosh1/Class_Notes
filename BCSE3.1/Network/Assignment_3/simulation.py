"""
simulation.py
=============
Discrete-event simulation engine for CSMA protocols.

Main entry point for running simulations.  Supports single-run and batch
modes via CLI, with optional Rich terminal dashboard.

Usage:
    # Single protocol run
    python3 simulation.py --protocol csma_cd --stations 5

    # p-Persistent with custom p
    python3 simulation.py --protocol p_persistent --stations 5 --p-value 0.3

    # All protocols comparison
    python3 simulation.py --protocol all --stations 5

    # With live dashboard
    python3 simulation.py --protocol csma_cd --stations 8 --dashboard

    # Custom parameters
    python3 simulation.py --protocol all --stations 10 --sim-time 500 \\
                          --frames 50 --slot-time 1.0 --frame-duration 10.0

Run standalone for self-tests:
    python3 simulation.py
"""

import argparse
import random
import sys
import time
from dataclasses import dataclass, field

from channel import Channel, ChannelState
from station import Station, StationState
from csma_protocols import (
    non_persistent_csma, one_persistent_csma,
    p_persistent_csma, csma_cd,
    Event, PROTOCOLS, PROTOCOL_NAMES, get_protocol_func,
)


# ---------------------------------------------------------------------------
# Simulation result
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    """Metrics collected from a single simulation run."""
    protocol:            str
    num_stations:        int
    p_value:             float
    total_collisions:    int   = 0
    total_frames_sent:   int   = 0
    total_attempts:      int   = 0
    total_dropped:       int   = 0
    avg_delay:           float = 0.0
    throughput:          float = 0.0
    channel_utilization: float = 0.0
    collision_rate:      float = 0.0
    elapsed_slots:       int   = 0
    wall_time_sec:       float = 0.0

    def summary_row(self) -> dict:
        """Return a dict suitable for CSV / table output."""
        return {
            "protocol":       self.protocol,
            "N":              self.num_stations,
            "p":              self.p_value,
            "collisions":     self.total_collisions,
            "frames_sent":    self.total_frames_sent,
            "attempts":       self.total_attempts,
            "dropped":        self.total_dropped,
            "avg_delay":      round(self.avg_delay, 4),
            "throughput":     round(self.throughput, 6),
            "utilization":    round(self.channel_utilization, 6),
            "collision_rate": round(self.collision_rate, 6),
        }

    def __str__(self) -> str:
        lines = [
            f"  Protocol       : {PROTOCOL_NAMES.get(self.protocol, self.protocol)}",
            f"  Stations (N)   : {self.num_stations}",
            f"  p-value        : {self.p_value}",
            f"  Collisions     : {self.total_collisions}",
            f"  Frames sent    : {self.total_frames_sent}",
            f"  Attempts       : {self.total_attempts}",
            f"  Dropped frames : {self.total_dropped}",
            f"  Avg delay      : {self.avg_delay:.2f} slots",
            f"  Throughput     : {self.throughput:.4f}",
            f"  Utilization    : {self.channel_utilization:.2%}",
            f"  Collision rate : {self.collision_rate:.2%}",
            f"  Wall time      : {self.wall_time_sec:.3f}s",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Simulation configuration
# ---------------------------------------------------------------------------

@dataclass
class SimConfig:
    """Tunable simulation parameters."""
    num_stations:       int   = 5
    simulation_slots:   int   = 1000     # total simulation slots
    slot_time:          float = 1.0      # slot duration (abstract time unit)
    frame_duration:     float = 10.0     # frame transmission time (in slots)
    propagation_delay:  float = 2.0      # one-way propagation delay (in slots)
    jam_duration:       float = 4.0      # jam signal duration (in slots)
    frames_per_station: int   = 100      # frames each station has to send
    p_value:            float = 0.3      # persistence probability
    max_retries:        int   = 16       # max BEB retries
    verbose:            bool  = False
    use_dashboard:      bool  = False
    seed:               int | None = None


# ---------------------------------------------------------------------------
# Core simulation engine
# ---------------------------------------------------------------------------

def run_simulation(protocol_name: str,
                   config: SimConfig,
                   dashboard=None) -> SimulationResult:
    """
    Run a single discrete-event simulation.

    The simulation advances slot-by-slot.  Each slot:
        1. Tick all station backoff timers.
        2. Each IDLE station with data executes the protocol decision.
        3. Check for collisions (2+ simultaneous transmitters).
        4. Handle collisions: abort, jam signal, BEB for all colliders.
        5. Check for completed transmissions.
        6. Record channel state for statistics.

    Parameters
    ----------
    protocol_name : str        – one of: non_persistent, 1_persistent, p_persistent, csma_cd
    config        : SimConfig  – simulation parameters
    dashboard     : Dashboard  – optional dashboard for live UI (or None)

    Returns
    -------
    SimulationResult
    """
    if config.seed is not None:
        random.seed(config.seed)

    # Initialize channel and stations
    channel = Channel(
        propagation_delay=config.propagation_delay,
        slot_time=config.slot_time,
    )
    stations = [
        Station(
            station_id=i,
            frames_to_send=config.frames_per_station,
            max_retries=config.max_retries,
        )
        for i in range(config.num_stations)
    ]

    protocol_func = get_protocol_func(protocol_name)

    # Tracking active transmissions: {station_id: end_time}
    active_tx: dict[int, float] = {}

    total_collisions = 0
    wall_start = time.time()

    # ---- Main simulation loop ----
    current_time = 0.0
    slot_count = 0

    while slot_count < config.simulation_slots:
        # Check if all stations are done
        all_done = all(s.state == StationState.DONE for s in stations)
        if all_done:
            break

        # Step 1: Tick backoff timers for WAITING stations
        for station in stations:
            station.tick_backoff(config.slot_time)

        # Step 2: Snapshot the channel state BEFORE any decisions,
        # then let every IDLE station decide independently based on
        # the same snapshot.  This models simultaneous sensing.
        channel_snapshot = channel.sense(current_time)

        # Collect which stations want to transmit this slot
        want_to_transmit: list[int] = []
        events: list[Event] = []

        for station in stations:
            if station.state != StationState.IDLE or not station.has_data():
                continue

            if channel_snapshot == ChannelState.IDLE:
                # Channel was idle at the start of this slot
                should_tx = False

                if protocol_name == "non_persistent":
                    should_tx = True  # non-persistent transmits when idle

                elif protocol_name == "1_persistent":
                    should_tx = True  # 1-persistent always transmits when idle

                elif protocol_name == "p_persistent":
                    r = random.random()
                    if r < config.p_value:
                        should_tx = True
                        events.append(Event(station.id, current_time, "TRANSMIT",
                                            f"p={config.p_value}, r={r:.3f} < p"))
                    else:
                        station.set_deferred(config.slot_time)
                        events.append(Event(station.id, current_time, "DEFER",
                                            f"p={config.p_value}, r={r:.3f} ≥ p"))

                elif protocol_name == "csma_cd":
                    should_tx = True  # CSMA/CD uses 1-persistent sensing

                if should_tx:
                    want_to_transmit.append(station.id)

            else:
                # Channel is BUSY or COLLISION
                if protocol_name == "non_persistent":
                    # Wait random time before re-sensing
                    wait_slots = random.randint(1, 10)
                    station.set_deferred(wait_slots * config.slot_time)
                    events.append(Event(station.id, current_time, "SENSE_BUSY",
                                        f"non-persistent wait={wait_slots} slots"))
                else:
                    # 1-persistent, p-persistent, CSMA/CD: keep sensing next slot
                    events.append(Event(station.id, current_time, "SENSE_BUSY",
                                        f"{protocol_name}: busy, retry next slot"))

        # Step 3: Apply all simultaneous transmission attempts
        for sid in want_to_transmit:
            frame = stations[sid].start_transmission(current_time)
            if frame is not None:
                channel.attempt_transmission(sid, current_time, config.frame_duration)
                active_tx[sid] = current_time + config.frame_duration
                events.append(Event(sid, current_time, "TRANSMIT",
                                    f"frame={frame}"))

        # Step 4: Check for collisions (2+ stations transmitted this slot)
        if channel.check_collision():
            total_collisions += 1
            collided_ids = channel.abort_all_transmissions(current_time)

            # Log collision
            if config.verbose:
                print(f"  [t={current_time:.0f}] COLLISION: stations {collided_ids}")
            if dashboard:
                dashboard.log_collision(current_time, collided_ids)

            # CSMA/CD: send jam signal
            if protocol_name == "csma_cd":
                channel.send_jam_signal(current_time, config.jam_duration)

            for sid in collided_ids:
                stations[sid].complete_transmission(success=False,
                                                    current_time=current_time)
                stations[sid].handle_collision(current_time, config.slot_time)
                if sid in active_tx:
                    del active_tx[sid]

            events.append(Event(-1, current_time, "COLLISION",
                                f"stations={collided_ids}"))

        # Step 5: Check for completed transmissions
        finished = [sid for sid, end in active_tx.items()
                    if current_time >= end]
        for sid in finished:
            stations[sid].complete_transmission(success=True,
                                                current_time=current_time)
            channel.end_transmission(sid, current_time)
            del active_tx[sid]

            if config.verbose:
                print(f"  [t={current_time:.0f}] Stn {sid}: frame delivered ✓")

        # Step 6: Record channel slot state
        channel.record_slot(current_time)

        # Step 7: Update dashboard (if enabled)
        if dashboard:
            dashboard.update(
                current_time=current_time,
                slot=slot_count,
                total_slots=config.simulation_slots,
                stations=stations,
                channel=channel,
                events=events,
            )
            # Add an artificial delay so the user can watch the dashboard live!
            # Since Rich Live updates 8 times a second (0.125s), throttling the loop
            # ensures we don't finish 1000 slots in 0.05 seconds.
            time.sleep(0.01)

        # Log verbose events
        if config.verbose:
            for ev in events:
                if ev.action not in ("COLLISION",):  # collision already logged
                    print(f"  {ev}")

        # Advance time
        current_time += config.slot_time
        slot_count += 1

    # ---- Collect results ----
    wall_time = time.time() - wall_start
    total_frames = sum(s.metrics["frames_sent"] for s in stations)
    total_attempts = sum(s.metrics["total_attempts"] for s in stations)
    total_dropped = sum(s.metrics["dropped_frames"] for s in stations)
    total_station_collisions = sum(s.metrics["total_collisions"] for s in stations)

    # Average delay across all stations
    total_delay = sum(s.metrics["total_delay"] for s in stations)
    avg_delay = total_delay / max(total_frames, 1)

    # Throughput: successful frames / total simulation time
    throughput = total_frames / max(slot_count, 1)

    # Channel utilization
    utilization = channel.get_utilization(slot_count)
    collision_rate = channel.get_collision_rate(slot_count)

    return SimulationResult(
        protocol=protocol_name,
        num_stations=config.num_stations,
        p_value=config.p_value,
        total_collisions=total_collisions,
        total_frames_sent=total_frames,
        total_attempts=total_attempts,
        total_dropped=total_dropped,
        avg_delay=avg_delay,
        throughput=throughput,
        channel_utilization=utilization,
        collision_rate=collision_rate,
        elapsed_slots=slot_count,
        wall_time_sec=wall_time,
    )


# ---------------------------------------------------------------------------
# Multi-protocol comparison
# ---------------------------------------------------------------------------

def run_all_protocols(config: SimConfig, dashboard=None) -> list[SimulationResult]:
    """Run all protocols sequentially and return their results."""
    results = []
    for proto in PROTOCOLS.keys():
        if config.verbose:
            print(f"\n--- Running {PROTOCOL_NAMES[proto]} ---")
        if dashboard:
            dashboard.reset(new_protocol=PROTOCOL_NAMES[proto])
        cfg = SimConfig(
            num_stations=config.num_stations,
            simulation_slots=config.simulation_slots,
            slot_time=config.slot_time,
            frame_duration=config.frame_duration,
            propagation_delay=config.propagation_delay,
            jam_duration=config.jam_duration,
            frames_per_station=config.frames_per_station,
            p_value=config.p_value,
            max_retries=config.max_retries,
            verbose=config.verbose,
            seed=config.seed,
        )
        result = run_simulation(proto, cfg, dashboard)
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# Pretty-print results table
# ---------------------------------------------------------------------------

def print_results_table(results: list[SimulationResult]) -> None:
    """Print a formatted comparison table of simulation results."""
    header = (f"{'Protocol':<22} {'N':>3} {'p':>5} {'Collisions':>11} "
              f"{'Frames':>7} {'Dropped':>8} {'AvgDelay':>9} "
              f"{'Throughput':>11} {'Util%':>7} {'Coll%':>7}")
    sep = "─" * len(header)

    print()
    print(sep)
    print(header)
    print(sep)

    for r in results:
        name = PROTOCOL_NAMES.get(r.protocol, r.protocol)
        print(f"{name:<22} {r.num_stations:>3} {r.p_value:>5.2f} "
              f"{r.total_collisions:>11} {r.total_frames_sent:>7} "
              f"{r.total_dropped:>8} {r.avg_delay:>9.2f} "
              f"{r.throughput:>11.4f} {r.channel_utilization:>6.2%} "
              f"{r.collision_rate:>6.2%}")

    print(sep)
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="CSMA Protocol Simulator — Assignment 3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 simulation.py --protocol csma_cd --stations 5
  python3 simulation.py --protocol all --stations 10
  python3 simulation.py --protocol p_persistent --stations 5 --p-value 0.3
  python3 simulation.py --protocol all --stations 8 --dashboard
        """,
    )

    parser.add_argument("--protocol", type=str, default="all",
                        choices=list(PROTOCOLS.keys()) + ["all"],
                        help="CSMA protocol to simulate (default: all)")
    parser.add_argument("--stations", "-N", type=int, default=5,
                        help="Number of contending stations (default: 5)")
    parser.add_argument("--p-value", "-p", type=float, default=0.3,
                        help="Persistence probability for p-persistent (default: 0.3)")
    parser.add_argument("--sim-time", type=int, default=1000,
                        help="Total simulation slots (default: 1000)")
    parser.add_argument("--frames", type=int, default=100,
                        help="Frames per station (default: 100)")
    parser.add_argument("--slot-time", type=float, default=1.0,
                        help="Slot duration (default: 1.0)")
    parser.add_argument("--frame-duration", type=float, default=10.0,
                        help="Frame transmission time in slots (default: 10.0)")
    parser.add_argument("--prop-delay", type=float, default=2.0,
                        help="One-way propagation delay in slots (default: 2.0)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print per-slot details")
    parser.add_argument("--dashboard", "-d", action="store_true",
                        help="Enable Rich terminal dashboard")

    return parser.parse_args()


def main():
    args = parse_args()

    config = SimConfig(
        num_stations=args.stations,
        simulation_slots=args.sim_time,
        slot_time=args.slot_time,
        frame_duration=args.frame_duration,
        propagation_delay=args.prop_delay,
        frames_per_station=args.frames,
        p_value=args.p_value,
        verbose=args.verbose,
        use_dashboard=args.dashboard,
        seed=args.seed,
    )

    # Dashboard setup
    dashboard = None
    if args.dashboard:
        try:
            from dashboard import Dashboard
            dashboard = Dashboard(
                protocol=args.protocol,
                num_stations=config.num_stations,
                total_frames=config.frames_per_station * config.num_stations,
            )
            dashboard.start()
        except ImportError:
            print("[WARN] Rich not installed. Running without dashboard.")
            print("       Install with: pip3 install rich")

    # Banner
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         CSMA Protocol Simulator — Assignment 3           ║")
    print("╠════════════════════════════════════════════════════════════╣")
    print(f"║  Stations (N)     : {config.num_stations:<37}║")
    print(f"║  Simulation slots : {config.simulation_slots:<37}║")
    print(f"║  Frame duration   : {config.frame_duration:<37}║")
    print(f"║  Prop. delay (τ)  : {config.propagation_delay:<37}║")
    print(f"║  p-value          : {config.p_value:<37}║")
    print(f"║  Frames/station   : {config.frames_per_station:<37}║")
    if args.seed is not None:
        print(f"║  Seed             : {args.seed:<37}║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    if args.protocol == "all":
        print("Running all four protocols...\n")
        results = run_all_protocols(config, dashboard)
        print_results_table(results)

        # Observations
        best_throughput = max(results, key=lambda r: r.throughput)
        least_collisions = min(results, key=lambda r: r.total_collisions)

        print("📊 Observations:")
        print(f"   Best throughput  : {PROTOCOL_NAMES[best_throughput.protocol]} "
              f"({best_throughput.throughput:.4f})")
        print(f"   Least collisions : {PROTOCOL_NAMES[least_collisions.protocol]} "
              f"({least_collisions.total_collisions})")
        print()
    else:
        print(f"Running {PROTOCOL_NAMES[args.protocol]}...\n")
        result = run_simulation(args.protocol, config, dashboard)

        print(f"\n{'─' * 50}")
        print(f"  Results: {PROTOCOL_NAMES[args.protocol]}")
        print(f"{'─' * 50}")
        print(result)
        print(f"{'─' * 50}\n")

    if dashboard:
        dashboard.stop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
