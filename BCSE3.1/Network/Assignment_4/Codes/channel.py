"""
channel.py
==========
Shared CDMA Broadcast Medium Simulation & Channel Server Process.

Models the physical layer channel where orthogonal chip sequences from
multiple independent station processes linearly superimpose into a composite signal.

Supports:
  - In-process / Pipe-based channel superposition
  - Standalone Channel Server process communicating with k separate terminal station processes over TCP sockets

Mathematics:
    Superposition:
        C = sum_{i=0}^{n-1} s_i

    Noisy Channel (AWGN):
        C_{noisy} = C + eta,   where eta ~ N(0, sigma^2)
"""

from __future__ import annotations
import os
import sys
import math
import json
import socket
import argparse
from collections import deque
import numpy as np

try:
    from walsh import WalshCodeGenerator
except ImportError:
    from Codes.walsh import WalshCodeGenerator


class Channel:
    """
    Simulates a shared CDMA common channel with linear superposition,
    optional AWGN noise, signal logging, and telemetry.
    """

    def __init__(self, code_length: int, snr_db: float | None = None):
        """
        Args:
            code_length: Length of the Walsh code (N chips per bit).
            snr_db: Optional signal-to-noise ratio in decibels. None = noiseless channel.
        """
        self.code_length = code_length
        self.snr_db = snr_db
        self.pid = os.getpid()

        # Current state
        self.state: str = "IDLE"  # "IDLE", "TRANSMITTING"
        self.current_composite_signal: np.ndarray = np.zeros(code_length, dtype=np.float64)
        self.current_noiseless_signal: np.ndarray = np.zeros(code_length, dtype=np.float64)
        self.current_noise_vector: np.ndarray = np.zeros(code_length, dtype=np.float64)

        # Statistics & telemetry
        self.total_slots: int = 0
        self.total_chips_transmitted: int = 0
        self.signal_history: deque[np.ndarray] = deque(maxlen=200)
        self.active_transmitters_count: int = 0

    def transmit_slot(self, station_signals: dict[int, np.ndarray | list[float]]) -> np.ndarray:
        """
        Superimposes chip signals from all active stations onto the common channel.

        Args:
            station_signals: Dictionary mapping station_id to its chip vector of length N.

        Returns:
            np.ndarray: Composite signal vector of length N present on the channel.
        """
        self.state = "TRANSMITTING"
        self.total_slots += 1
        self.active_transmitters_count = len(station_signals)

        # Linear Superposition: sum of all station chip vectors
        composite = np.zeros(self.code_length, dtype=np.float64)
        for st_id, chips in station_signals.items():
            if chips is not None:
                composite += np.array(chips, dtype=np.float64)

        self.current_noiseless_signal = composite.copy()

        # Inject AWGN noise if SNR is configured
        if self.snr_db is not None:
            noisy_composite, noise = self._apply_awgn(composite, self.snr_db)
            self.current_composite_signal = noisy_composite
            self.current_noise_vector = noise
        else:
            self.current_composite_signal = composite.copy()
            self.current_noise_vector = np.zeros(self.code_length, dtype=np.float64)

        self.total_chips_transmitted += self.code_length
        self.signal_history.append(self.current_composite_signal.copy())
        return self.current_composite_signal.copy()

    def _apply_awgn(self, signal: np.ndarray, snr_db: float) -> tuple[np.ndarray, np.ndarray]:
        """Applies Additive White Gaussian Noise (AWGN) to signal vector."""
        signal_power = np.mean(signal ** 2)
        if signal_power == 0:
            signal_power = 1.0

        snr_linear = 10.0 ** (snr_db / 10.0)
        noise_variance = signal_power / snr_linear
        noise_std = math.sqrt(noise_variance)

        noise = np.random.normal(0.0, noise_std, size=signal.shape)
        noisy_signal = signal + noise
        return noisy_signal, noise

    def get_latest_signal(self) -> np.ndarray:
        return self.current_composite_signal.copy()

    def reset(self) -> None:
        self.state = "IDLE"
        self.current_composite_signal = np.zeros(self.code_length, dtype=np.float64)
        self.current_noiseless_signal = np.zeros(self.code_length, dtype=np.float64)
        self.current_noise_vector = np.zeros(self.code_length, dtype=np.float64)
        self.total_slots = 0
        self.total_chips_transmitted = 0
        self.signal_history.clear()
        self.active_transmitters_count = 0


# ---------------------------------------------------------------------------
# Standalone Socket Channel Server (Runs as Independent OS Server Process)
# ---------------------------------------------------------------------------

def run_socket_channel_server(host: str = "127.0.0.1",
                              port: int = 9000,
                              num_stations: int = 4,
                              total_slots: int = 32,
                              snr_db: float | None = None) -> None:
    """
    Runs a standalone Channel Hub server.
    Waits for k independent station processes to connect, distributes Walsh codes,
    and coordinates lockstep CDMA slot transmissions.
    """
    pid = os.getpid()
    print(f"\n=======================================================")
    print(f"  CDMA SHARED CHANNEL SERVER (PID {pid})")
    print(f"  Listening on {host}:{port} for {num_stations} Station Processes")
    print(f"=======================================================\n")

    H, code_len = WalshCodeGenerator.get_walsh_set(num_stations)
    channel = Channel(code_length=code_len, snr_db=snr_db)

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(num_stations)

    # Accept connections from k station processes
    station_conns: dict[int, socket.socket] = {}
    station_buffers: dict[int, str] = {}
    station_pids: dict[int, int] = {}

    print(f"[Channel] Waiting for {num_stations} station processes to connect...")
    while len(station_conns) < num_stations:
        client_sock, client_addr = server_sock.accept()
        # Read registration line
        line = client_sock.makefile("r").readline()
        reg = json.loads(line)
        st_id = reg["station_id"]
        st_pid = reg.get("pid", "Unknown")
        station_conns[st_id] = client_sock
        station_buffers[st_id] = ""
        station_pids[st_id] = st_pid
        print(f" -> Station {st_id} (Process PID {st_pid}) connected from {client_addr} [{len(station_conns)}/{num_stations}]")

        # Send configuration & allocated Walsh codeword
        cfg_msg = json.dumps({
            "type": "CONFIG",
            "station_id": st_id,
            "walsh_code": H[st_id].tolist(),
            "code_length": code_len,
            "total_slots": total_slots
        }) + "\n"
        client_sock.sendall(cfg_msg.encode("utf-8"))

    # Wait for all stations to acknowledge READY
    print("\n[Channel] All stations connected. Verifying READY handshake...")
    for st_id, sock in station_conns.items():
        line = sock.makefile("r").readline()
        ready_msg = json.loads(line)
        print(f" -> Station {st_id} (PID {station_pids[st_id]}) READY acknowledged.")

    print(f"\n[Channel] Starting synchronous slotted transmission ({total_slots} slots)...\n")

    for slot in range(total_slots):
        # 1. Request chip sequence from each station process
        station_chips: dict[int, list[float]] = {}
        station_bits: dict[int, int | None] = {}

        req_msg = (json.dumps({"type": "REQUEST_CHIPS", "slot": slot}) + "\n").encode("utf-8")
        for st_id, sock in station_conns.items():
            sock.sendall(req_msg)

        # Collect chips from all k stations
        for st_id, sock in station_conns.items():
            line = sock.makefile("r").readline()
            resp = json.loads(line)
            station_chips[st_id] = resp["chips"]
            station_bits[st_id] = resp["bit"]

        # 2. Linear Superposition on Channel
        composite = channel.transmit_slot(station_chips)

        # 3. Broadcast composite vector back to all k stations
        bcast_msg = (json.dumps({"type": "BROADCAST_COMPOSITE", "slot": slot, "composite": composite.tolist()}) + "\n").encode("utf-8")
        for st_id, sock in station_conns.items():
            sock.sendall(bcast_msg)

        # Collect decoding confirmation
        decoded_bits = {}
        for st_id, sock in station_conns.items():
            line = sock.makefile("r").readline()
            resp = json.loads(line)
            decoded_bits[st_id] = resp["decoded_bit"]

        # Verify matches
        matches = [station_bits[i] == decoded_bits[i] for i in range(num_stations)]
        status = "ALL MATCH [OK]" if all(matches) else "MISMATCH"
        print(f"Slot {slot:2d} | C = {composite.tolist()} | Bits TX: {station_bits} | Bits RX: {decoded_bits} | {status}")

    # Terminate session
    print("\n[Channel] Transmission completed. Sending TERMINATE to all station processes...")
    term_msg = (json.dumps({"type": "TERMINATE"}) + "\n").encode("utf-8")
    for st_id, sock in station_conns.items():
        sock.sendall(term_msg)
        sock.close()

    server_sock.close()
    print("[Channel] Server shutdown cleanly.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CDMA Shared Channel")
    parser.add_argument("--serve", action="store_true", help="Run standalone Channel TCP server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=9000, help="Server port")
    parser.add_argument("--stations", type=int, default=4, help="Number of station processes to wait for")
    parser.add_argument("--slots", type=int, default=32, help="Number of transmission slots")
    parser.add_argument("--snr", type=float, default=None, help="Channel SNR in dB")
    args = parser.parse_args()

    if args.serve:
        run_socket_channel_server(host=args.host, port=args.port, num_stations=args.stations, total_slots=args.slots, snr_db=args.snr)
    else:
        print("=== Self-Test: CDMA Shared Channel ===")
        chan = Channel(code_length=4)
        sig_a = np.array([1, 1, 1, 1])
        sig_b = np.array([1, -1, 1, -1])
        comp = chan.transmit_slot({0: sig_a, 1: sig_b})
        print(f"Signal A: {sig_a}")
        print(f"Signal B: {sig_b}")
        print(f"Superposed Channel Signal C: {comp}")
        print(f"Total Chips Transmitted: {chan.total_chips_transmitted}")
