"""
simulation.py
=============
Multi-Process and Discrete-Time CDMA Simulation Engine.

Directly satisfies the architectural requirement:
  "CDMA shouldn't be a single standalone process, if there are k no of stations
   sharing the same channel there should be k processes."

Classes:
  - MultiProcessCDMASimulation: Spawns k true independent OS child processes
    using multiprocessing.Process, managing IPC communication over duplex Pipes.
  - CDMASimulation: Lightweight in-memory simulation engine for fast Monte Carlo sweeps.
"""

from __future__ import annotations
import os
import time
import multiprocessing as mp
from typing import Callable, Any
import numpy as np

try:
    from walsh import WalshCodeGenerator
    from channel import Channel
    from station import Station, station_process_worker
except ImportError:
    from Codes.walsh import WalshCodeGenerator
    from Codes.channel import Channel
    from Codes.station import Station, station_process_worker


class MultiProcessCDMASimulation:
    """
    True multi-process CDMA network simulation coordinator.
    Spawns k independent OS processes (one per station),
    communicating with the Channel orchestrator via duplex IPC Pipes.
    """

    def __init__(self,
                 num_stations: int = 4,
                 snr_db: float | None = None,
                 payloads: list[str | list[int | None]] | None = None):
        """
        Args:
            num_stations: Number of transmitting/receiving stations (spawns k OS processes).
            snr_db: Signal-to-Noise Ratio in dB (None for noiseless channel).
            payloads: List of payloads (strings or bit lists) for each station.
        """
        self.num_stations = num_stations
        self.snr_db = snr_db
        self.main_pid = os.getpid()

        # Initialize Walsh codes
        self.hadamard_matrix, self.code_length = WalshCodeGenerator.get_walsh_set(num_stations)
        self.is_orthogonal, self.gramian = WalshCodeGenerator.verify_orthogonality(self.hadamard_matrix)

        # Initialize Channel
        self.channel = Channel(code_length=self.code_length, snr_db=self.snr_db)

        # Multi-process management structures
        self.processes: dict[int, mp.Process] = {}
        self.channel_pipes: dict[int, Any] = {}
        self.station_pids: dict[int, int] = {}
        self.station_names: dict[int, str] = {}
        self.station_walsh_codes: dict[int, np.ndarray] = {}

        # Payloads
        if payloads is None:
            sample_messages = ["NETWK_A", "HELLO_B", "CDMA_TX", "PACKET4", "SIGNAL5", "MODEM_6", "RADIO_7", "CIPHER8"]
            self.payloads = [sample_messages[i % len(sample_messages)] for i in range(num_stations)]
        else:
            self.payloads = list(payloads)

        # Calculate planned slots
        max_slots = 0
        for p in self.payloads:
            if isinstance(p, str):
                max_slots = max(max_slots, len(p) * 8)
            else:
                max_slots = max(max_slots, len(p))
        self.total_slots_planned = max_slots

        self.current_slot: int = 0
        self.is_completed: bool = False
        self.slot_history: list[dict[str, Any]] = []

        # Spawn all k OS processes
        self._spawn_processes()

    def _spawn_processes(self) -> None:
        """
        Spawns k independent OS processes, establishes IPC pipes,
        and executes handshake.
        """
        for i in range(self.num_stations):
            walsh_code = self.hadamard_matrix[i].copy()
            payload = self.payloads[i] if i < len(self.payloads) else "IDLE"

            # Create duplex IPC Pipe
            channel_conn, station_conn = mp.Pipe(duplex=True)
            self.channel_pipes[i] = channel_conn

            # Spawn child process
            proc = mp.Process(
                target=station_process_worker,
                args=(i, walsh_code, payload, station_conn),
                name=f"StationProcess-{i}",
                daemon=True
            )
            proc.start()
            self.processes[i] = proc
            self.station_walsh_codes[i] = walsh_code

        # Complete handshake and record child PIDs
        for i in range(self.num_stations):
            ready_msg = self.channel_pipes[i].recv()
            child_pid = ready_msg["pid"]
            self.station_pids[i] = child_pid
            self.station_names[i] = f"Station_{i} (PID {child_pid})"

    def step(self) -> dict[str, Any]:
        """
        Executes a single synchronous bit transmission slot across all k OS processes.

        Returns:
            dict[str, Any]: Telemetry detailing chip sequences, channel signal, decodings, and PIDs.
        """
        if self.is_completed:
            return {}

        # 1. Transmitter Phase: Request chips from all k independent station processes
        for i in range(self.num_stations):
            self.channel_pipes[i].send({"type": "REQUEST_CHIPS", "slot": self.current_slot})

        active_chips: dict[int, np.ndarray] = {}
        tx_bits: dict[int, int | None] = {}
        tx_bipolar: dict[int, int] = {}

        for i in range(self.num_stations):
            resp = self.channel_pipes[i].recv()
            bit = resp["bit"]
            chips = np.array(resp["chips"], dtype=np.int32)
            active_chips[i] = chips
            tx_bits[i] = bit
            tx_bipolar[i] = 1 if bit == 1 else (-1 if bit == 0 else 0)

        # 2. Channel Phase: Superimpose chip sequences onto the shared medium
        composite_signal = self.channel.transmit_slot(active_chips)

        # 3. Receiver Phase: Broadcast composite vector back to all k station processes
        bcast_msg = {"type": "BROADCAST_COMPOSITE", "slot": self.current_slot, "composite": composite_signal.tolist()}
        for i in range(self.num_stations):
            self.channel_pipes[i].send(bcast_msg)

        rx_bits: dict[int, int | None] = {}
        rx_norms: dict[int, float] = {}
        reconstructed_msgs: dict[int, str] = {}
        matches: dict[int, bool] = {}

        for i in range(self.num_stations):
            resp = self.channel_pipes[i].recv()
            rx_bits[i] = resp["decoded_bit"]
            rx_norms[i] = resp["norm"]
            reconstructed_msgs[i] = resp["reconstructed_msg"]
            matches[i] = (tx_bits[i] == rx_bits[i])

        telemetry = {
            "slot": self.current_slot,
            "main_pid": self.main_pid,
            "station_pids": self.station_pids.copy(),
            "tx_bits": tx_bits,
            "tx_bipolar": tx_bipolar,
            "station_chips": active_chips,
            "composite_signal": composite_signal,
            "noiseless_signal": self.channel.current_noiseless_signal.copy(),
            "noise_vector": self.channel.current_noise_vector.copy(),
            "rx_bits": rx_bits,
            "rx_norms": rx_norms,
            "reconstructed_msgs": reconstructed_msgs,
            "matches": matches,
            "all_matched": all(matches.values())
        }

        self.slot_history.append(telemetry)
        self.current_slot += 1

        if self.current_slot >= self.total_slots_planned:
            self.is_completed = True

        return telemetry

    def run_all(self, slot_callback: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
        """
        Executes the entire multi-process simulation to completion.
        """
        while not self.is_completed:
            telem = self.step()
            if slot_callback:
                slot_callback(telem)

        return self.terminate_and_report()

    def terminate_and_report(self) -> dict[str, Any]:
        """
        Sends TERMINATE to all k OS processes, collects final reports,
        and joins processes cleanly.
        """
        term_msg = {"type": "TERMINATE"}
        for i in range(self.num_stations):
            try:
                self.channel_pipes[i].send(term_msg)
            except Exception:
                pass

        station_reports = []
        total_errors = 0
        total_bits = 0

        for i in range(self.num_stations):
            try:
                rep = self.channel_pipes[i].recv()
            except EOFError:
                rep = {"is_perfect": False, "errors": 0, "ber": 1.0, "tx_message": "", "rx_message": "", "total_tx_bits": 0, "total_rx_bits": 0}

            total_errors += rep["errors"]
            total_bits += rep.get("total_tx_bits", 0)

            station_reports.append({
                "station_id": i,
                "pid": self.station_pids.get(i, 0),
                "name": self.station_names.get(i, f"Station_{i}"),
                "walsh_code": WalshCodeGenerator.format_code(self.station_walsh_codes[i]),
                "tx_bits_count": rep.get("total_tx_bits", 0),
                "rx_bits_count": rep.get("total_rx_bits", 0),
                "transmitted_message": rep["tx_message"],
                "reconstructed_message": rep["rx_message"],
                "bit_errors": rep["errors"],
                "ber": rep["ber"],
                "is_perfect": rep["is_perfect"]
            })

            # Close pipe
            self.channel_pipes[i].close()

        # Join all child processes
        for i, proc in self.processes.items():
            proc.join(timeout=2.0)
            if proc.is_alive():
                proc.terminate()

        overall_ber = (total_errors / total_bits) if total_bits > 0 else 0.0
        all_perfect = all(r["is_perfect"] for r in station_reports)

        return {
            "num_stations": self.num_stations,
            "code_length": self.code_length,
            "snr_db": self.snr_db,
            "main_pid": self.main_pid,
            "station_pids": self.station_pids,
            "total_slots": self.current_slot,
            "total_bits": total_bits,
            "total_errors": total_errors,
            "overall_ber": overall_ber,
            "all_perfect": all_perfect,
            "orthogonality_verified": self.is_orthogonal,
            "station_reports": station_reports
        }


# ---------------------------------------------------------------------------
# In-Memory Simulation Class (For Fast Sweeps & Standalone Verification)
# ---------------------------------------------------------------------------

class CDMASimulation:
    """
    In-memory simulation coordinator for synchronous CDMA communications.
    Used for rapid Monte Carlo sweeps.
    """

    def __init__(self,
                 num_stations: int = 4,
                 snr_db: float | None = None,
                 payloads: list[str | list[int | None]] | None = None):
        self.num_stations = num_stations
        self.snr_db = snr_db

        self.hadamard_matrix, self.code_length = WalshCodeGenerator.get_walsh_set(num_stations)
        self.is_orthogonal, self.gramian = WalshCodeGenerator.verify_orthogonality(self.hadamard_matrix)
        self.channel = Channel(code_length=self.code_length, snr_db=self.snr_db)

        self.stations: list[Station] = []
        for i in range(num_stations):
            st = Station(station_id=i, walsh_code=self.hadamard_matrix[i], name=f"Station_{i}")
            self.stations.append(st)

        self.current_slot: int = 0
        self.total_slots_planned: int = 0
        self.is_completed: bool = False
        self.slot_history: list[dict[str, Any]] = []

        if payloads is not None:
            self.load_payloads(payloads)

    def load_payloads(self, payloads: list[str | list[int | None]]) -> None:
        for i, payload in enumerate(payloads):
            if i < len(self.stations):
                self.stations[i].load_payload(payload)
        max_bits = max(len(st.sender.bit_queue) for st in self.stations)
        self.total_slots_planned = max_bits
        self.current_slot = 0
        self.is_completed = False
        self.slot_history.clear()

    def load_default_text_payloads(self) -> None:
        sample_messages = ["NETWK_A", "HELLO_B", "CDMA_TX", "PACKET4", "SIGNAL5", "MODEM_6", "RADIO_7", "CIPHER8"]
        payloads = [sample_messages[i % len(sample_messages)] for i in range(self.num_stations)]
        self.load_payloads(payloads)

    def step(self) -> dict[str, Any]:
        if self.is_completed:
            return {}

        active_chips: dict[int, np.ndarray] = {}
        tx_bits: dict[int, int | None] = {}
        tx_bipolar: dict[int, int] = {}

        for st in self.stations:
            chips = st.produce_chips()
            active_chips[st.station_id] = chips
            tx_bits[st.station_id] = st.sender.current_bit
            tx_bipolar[st.station_id] = 1 if st.sender.current_bit == 1 else (-1 if st.sender.current_bit == 0 else 0)

        composite_signal = self.channel.transmit_slot(active_chips)

        rx_bits: dict[int, int | None] = {}
        rx_norms: dict[int, float] = {}
        reconstructed_msgs: dict[int, str] = {}
        matches: dict[int, bool] = {}

        for st in self.stations:
            decoded_bit, norm_val = st.receive_channel_signal(composite_signal)
            rx_bits[st.station_id] = decoded_bit
            rx_norms[st.station_id] = norm_val
            reconstructed_msgs[st.station_id] = st.receiver.get_message()
            matches[st.station_id] = (tx_bits[st.station_id] == decoded_bit)

        telemetry = {
            "slot": self.current_slot,
            "station_pids": {st.station_id: st.pid for st in self.stations},
            "tx_bits": tx_bits,
            "tx_bipolar": tx_bipolar,
            "station_chips": active_chips,
            "composite_signal": composite_signal,
            "noiseless_signal": self.channel.current_noiseless_signal.copy(),
            "noise_vector": self.channel.current_noise_vector.copy(),
            "rx_bits": rx_bits,
            "rx_norms": rx_norms,
            "reconstructed_msgs": reconstructed_msgs,
            "matches": matches,
            "all_matched": all(matches.values())
        }

        self.slot_history.append(telemetry)
        self.current_slot += 1

        any_pending = any(st.sender.has_pending_data() for st in self.stations)
        if not any_pending:
            self.is_completed = True

        return telemetry

    def run_all(self, slot_callback: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
        while not self.is_completed:
            telem = self.step()
            if slot_callback:
                slot_callback(telem)
        return self.generate_summary_report()

    def generate_summary_report(self) -> dict[str, Any]:
        station_reports = []
        total_errors = 0
        total_bits = 0

        for st in self.stations:
            is_perfect, errors, ber = st.verify_reconstruction()
            total_errors += errors
            total_bits += len(st.sender.transmitted_bits)
            station_reports.append({
                "station_id": st.station_id,
                "pid": st.pid,
                "name": st.name,
                "walsh_code": WalshCodeGenerator.format_code(st.walsh_code),
                "tx_bits_count": len(st.sender.transmitted_bits),
                "rx_bits_count": len(st.receiver.received_bits),
                "transmitted_message": st.sender.raw_message,
                "reconstructed_message": st.receiver.get_message(),
                "bit_errors": errors,
                "ber": ber,
                "is_perfect": is_perfect
            })

        overall_ber = (total_errors / total_bits) if total_bits > 0 else 0.0
        all_perfect = all(rep["is_perfect"] for rep in station_reports)

        return {
            "num_stations": self.num_stations,
            "code_length": self.code_length,
            "snr_db": self.snr_db,
            "total_slots": self.current_slot,
            "total_bits": total_bits,
            "total_errors": total_errors,
            "overall_ber": overall_ber,
            "all_perfect": all_perfect,
            "orthogonality_verified": self.is_orthogonal,
            "station_reports": station_reports
        }


if __name__ == "__main__":
    print("=== Self-Test: Multi-Process CDMA Simulation ===")
    sim = MultiProcessCDMASimulation(num_stations=4, payloads=["A", "B", "C", "D"])
    print(f"Main Process PID: {sim.main_pid}")
    print(f"Spawned Station PIDs: {sim.station_pids}")
    rep = sim.run_all()
    print(f"All Perfect Reconstruction: {rep['all_perfect']}")
    for s_rep in rep["station_reports"]:
        print(f"Station {s_rep['station_id']} [PID {s_rep['pid']}]: Sent '{s_rep['transmitted_message']}' -> Received '{s_rep['reconstructed_message']}' (Exact: {s_rep['is_perfect']})")
