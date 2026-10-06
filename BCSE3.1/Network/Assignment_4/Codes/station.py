"""
station.py
==========
CDMA Network Station, Sender, and Receiver Architecture.

Supports both in-process encapsulation and TRUE MULTI-PROCESS execution:
  - Sender: Converts source data (bits or ASCII text) to bipolar symbols and spreads with Walsh code.
  - Receiver: Correlates the composite channel vector with the assigned Walsh code to extract the original bit.
  - Station: Unified node encapsulation managing communication state, telemetry, and verification.
  - station_process_worker(): Target function for independent OS worker processes communicating via IPC Pipes.
  - run_socket_station_client(): Standalone terminal process communicating with a Channel server over TCP sockets.

Mathematics:
    Bipolar Encoding:
        b = 1    ==> d = +1
        b = 0    ==> d = -1
        b = None ==> d =  0 (Silent / Idle)

    Spreading:
        s_i = d_i * W_i   (Vector of length N)

    Despreading (Correlator Receiver):
        Y_i = C · W_i = sum_{k=0}^{N-1} C[k] * W_i[k]
        d_hat = Y_i / N

    Decision Rule:
        b_hat = 1     if d_hat > 0.5
        b_hat = 0     if d_hat < -0.5
        b_hat = None  if |d_hat| <= 0.5 (Idle)
"""

from __future__ import annotations
import os
import sys
import json
import socket
import argparse
import numpy as np


class Sender:
    """
    CDMA Transmitter unit for a station.
    Encodes binary/text payloads into orthogonal chip sequences.
    """

    def __init__(self, station_id: int, walsh_code: np.ndarray):
        self.station_id = station_id
        self.walsh_code = np.array(walsh_code, dtype=np.int32)
        self.code_length = len(walsh_code)

        # Transmission buffers
        self.bit_queue: list[int | None] = []
        self.transmitted_bits: list[int | None] = []
        self.raw_message: str = ""
        self.current_bit: int | None = None
        self.current_chips: np.ndarray | None = None
        self.state: str = "IDLE"  # "IDLE", "TRANSMITTING", "COMPLETED"

    def load_bits(self, bits: list[int | None]) -> None:
        """Loads a sequence of binary bits (or None for idle slots) to transmit."""
        self.bit_queue = list(bits)
        self.transmitted_bits = []
        self.state = "IDLE" if not bits else "TRANSMITTING"

    def load_text(self, text: str) -> None:
        """Converts ASCII text to an 8-bit per character sequence and loads into queue."""
        self.raw_message = text
        bits: list[int | None] = []
        for char in text:
            byte_val = ord(char)
            # 8 bits MSB first
            for bit_pos in range(7, -1, -1):
                bits.append((byte_val >> bit_pos) & 1)
        self.load_bits(bits)

    def get_next_chips(self) -> np.ndarray:
        """
        Pulls the next bit from queue, converts to bipolar chip sequence,
        and logs the transmission.
        """
        if not self.bit_queue:
            self.current_bit = None
            self.current_chips = np.zeros(self.code_length, dtype=np.int32)
            self.state = "COMPLETED"
            return self.current_chips.copy()

        bit = self.bit_queue.pop(0)
        self.current_bit = bit
        self.transmitted_bits.append(bit)

        # Bipolar mapping
        if bit == 1:
            bipolar = 1
        elif bit == 0:
            bipolar = -1
        else:
            bipolar = 0  # Idle / silent

        self.current_chips = bipolar * self.walsh_code
        self.state = "TRANSMITTING" if self.bit_queue else "COMPLETED"
        return self.current_chips.copy()

    def has_pending_data(self) -> bool:
        """Returns True if there are bits remaining to transmit."""
        return len(self.bit_queue) > 0


class Receiver:
    """
    CDMA Receiver unit for a station.
    Implements a matched filter / despreader correlator.
    """

    def __init__(self, station_id: int, walsh_code: np.ndarray):
        self.station_id = station_id
        self.walsh_code = np.array(walsh_code, dtype=np.int32)
        self.code_length = len(walsh_code)

        # Reception buffers
        self.received_bits: list[int | None] = []
        self.received_symbols: list[float] = []
        self.reconstructed_message: str = ""
        self._char_bit_buffer: list[int] = []
        self.state: str = "IDLE"  # "IDLE", "RECEIVING", "COMPLETED"

    def decode_chips(self, composite_signal: np.ndarray) -> tuple[int | None, float]:
        """
        Despreads composite signal using the station's assigned Walsh code.

        Args:
            composite_signal: Vector of length N from common channel.

        Returns:
            tuple[int | None, float]: (decoded_bit, normalized_correlation).
        """
        self.state = "RECEIVING"
        # Inner product: correlation with assigned Walsh code
        dot_product = float(np.dot(composite_signal, self.walsh_code))
        normalized = dot_product / self.code_length
        self.received_symbols.append(normalized)

        # Decision Thresholding
        if normalized > 0.5:
            decoded_bit = 1
        elif normalized < -0.5:
            decoded_bit = 0
        else:
            decoded_bit = None  # Silent / Idle

        self.received_bits.append(decoded_bit)

        # Reconstruct text if receiving valid bits
        if decoded_bit is not None:
            self._char_bit_buffer.append(decoded_bit)
            if len(self._char_bit_buffer) == 8:
                char_code = 0
                for b in self._char_bit_buffer:
                    char_code = (char_code << 1) | b
                self.reconstructed_message += chr(char_code)
                self._char_bit_buffer = []

        return decoded_bit, normalized

    def get_message(self) -> str:
        """Returns reconstructed ASCII text message."""
        return self.reconstructed_message

    def reset(self) -> None:
        """Resets receiver buffers."""
        self.received_bits.clear()
        self.received_symbols.clear()
        self.reconstructed_message = ""
        self._char_bit_buffer.clear()
        self.state = "IDLE"


class Station:
    """
    Represents an autonomous station in the CDMA network,
    coupling a Sender and a Receiver with telemetry and verification.
    """

    def __init__(self, station_id: int, walsh_code: np.ndarray, name: str | None = None):
        self.station_id = station_id
        self.walsh_code = np.array(walsh_code, dtype=np.int32)
        self.code_length = len(walsh_code)
        self.pid = os.getpid()
        self.name = name or f"Station_{station_id} (PID {self.pid})"

        self.sender = Sender(station_id, self.walsh_code)
        self.receiver = Receiver(station_id, self.walsh_code)

    def load_payload(self, text_or_bits: str | list[int | None]) -> None:
        """Loads payload into the station's transmitter."""
        if isinstance(text_or_bits, str):
            self.sender.load_text(text_or_bits)
        else:
            self.sender.load_bits(text_or_bits)

    def produce_chips(self) -> np.ndarray:
        """Transmits the next chip sequence onto the channel."""
        return self.sender.get_next_chips()

    def receive_channel_signal(self, composite_signal: np.ndarray) -> tuple[int | None, float]:
        """Receives and decodes the composite channel signal."""
        return self.receiver.decode_chips(composite_signal)

    def verify_reconstruction(self) -> tuple[bool, int, float]:
        """
        Compares transmitted bits against received bits.
        Correctly handles variable payload lengths across stations where
        shorter messages result in trailing idle (None) slots.

        Returns:
            tuple[bool, int, float]: (is_perfect, bit_errors, bit_error_rate).
        """
        tx = self.sender.transmitted_bits
        rx = self.receiver.received_bits

        if not tx:
            return True, 0, 0.0

        errors = 0
        for i in range(len(tx)):
            if i >= len(rx):
                errors += 1
            elif tx[i] != rx[i]:
                errors += 1

        # Check trailing received slots if any (should be idle/None)
        for i in range(len(tx), len(rx)):
            if rx[i] is not None:
                errors += 1

        ber = errors / len(tx) if len(tx) > 0 else 0.0
        # If ASCII messages exist, verify textual match as well
        if self.sender.raw_message:
            text_match = (self.sender.raw_message == self.receiver.get_message())
            is_perfect = (errors == 0) and text_match
        else:
            is_perfect = (errors == 0)

        return is_perfect, errors, ber

    def reset(self) -> None:
        """Resets station buffers."""
        self.sender.transmitted_bits.clear()
        self.sender.bit_queue.clear()
        self.sender.current_bit = None
        self.sender.current_chips = None
        self.sender.state = "IDLE"
        self.receiver.reset()


# ---------------------------------------------------------------------------
# Multi-Process Worker Function (Executed in an Independent OS Process)
# ---------------------------------------------------------------------------

def station_process_worker(station_id: int,
                           walsh_code: np.ndarray,
                           payload: str | list[int | None],
                           pipe_conn) -> None:
    """
    Target entry point executed inside an independent child OS process.
    Communicates with the Channel process through an IPC Pipe.

    Protocol:
      1. On start: Sends {"type": "READY", "pid": PID}
      2. On "REQUEST_CHIPS": Produces chips and sends {"type": "CHIPS", "chips": ...}
      3. On "BROADCAST_COMPOSITE": Despreads composite vector and sends {"type": "DECODED", ...}
      4. On "TERMINATE": Generates final report, sends {"type": "REPORT", ...}, and exits cleanly.
    """
    pid = os.getpid()
    station = Station(station_id, walsh_code, name=f"Station_{station_id} (PID {pid})")
    station.load_payload(payload)

    # Handshake with channel orchestrator
    pipe_conn.send({
        "type": "READY",
        "station_id": station_id,
        "pid": pid,
        "code_length": len(walsh_code)
    })

    while True:
        try:
            msg = pipe_conn.recv()
        except EOFError:
            break

        msg_type = msg.get("type")

        if msg_type == "REQUEST_CHIPS":
            chips = station.produce_chips()
            bit = station.sender.current_bit
            pipe_conn.send({
                "type": "CHIPS",
                "station_id": station_id,
                "pid": pid,
                "bit": bit,
                "chips": chips.tolist()
            })

        elif msg_type == "BROADCAST_COMPOSITE":
            composite = np.array(msg["composite"], dtype=np.float64)
            decoded_bit, norm_val = station.receive_channel_signal(composite)
            pipe_conn.send({
                "type": "DECODED",
                "station_id": station_id,
                "pid": pid,
                "decoded_bit": decoded_bit,
                "norm": norm_val,
                "reconstructed_msg": station.receiver.get_message()
            })

        elif msg_type == "TERMINATE":
            is_perfect, errors, ber = station.verify_reconstruction()
            pipe_conn.send({
                "type": "REPORT",
                "station_id": station_id,
                "pid": pid,
                "is_perfect": is_perfect,
                "errors": errors,
                "ber": ber,
                "tx_message": station.sender.raw_message,
                "rx_message": station.receiver.get_message(),
                "total_tx_bits": len(station.sender.transmitted_bits),
                "total_rx_bits": len(station.receiver.received_bits)
            })
            break

    pipe_conn.close()


# ---------------------------------------------------------------------------
# Standalone Socket Client (For Independent Terminal Windows)
# ---------------------------------------------------------------------------

def run_socket_station_client(station_id: int,
                              host: str = "127.0.0.1",
                              port: int = 9000,
                              payload: str = "HELLO") -> None:
    """
    Connects to a running Channel Server over TCP socket as an independent terminal process.
    """
    pid = os.getpid()
    print(f"[Station Process {station_id} | PID {pid}] Connecting to Channel Server at {host}:{port}...")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
    except ConnectionRefusedError:
        print(f"[ERROR] Could not connect to Channel Server at {host}:{port}. Is channel.py --serve running?")
        sys.exit(1)

    # Initial registration: send station_id
    reg = json.dumps({"type": "REGISTER", "station_id": station_id, "pid": pid}) + "\n"
    s.sendall(reg.encode("utf-8"))

    # Receive configuration from server (including assigned Walsh code)
    buffer = ""
    station = None

    while True:
        data = s.recv(4096).decode("utf-8")
        if not data:
            break
        buffer += data

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if not line.strip():
                continue
            msg = json.loads(line)
            m_type = msg.get("type")

            if m_type == "CONFIG":
                walsh_code = np.array(msg["walsh_code"], dtype=np.int32)
                station = Station(station_id, walsh_code)
                station.load_payload(payload)
                print(f"[Station {station_id} | PID {pid}] Registered! Walsh Code: {walsh_code.tolist()}")
                ack = json.dumps({"type": "READY", "station_id": station_id, "pid": pid}) + "\n"
                s.sendall(ack.encode("utf-8"))

            elif m_type == "REQUEST_CHIPS":
                chips = station.produce_chips()
                resp = json.dumps({
                    "type": "CHIPS",
                    "station_id": station_id,
                    "pid": pid,
                    "bit": station.sender.current_bit,
                    "chips": chips.tolist()
                }) + "\n"
                s.sendall(resp.encode("utf-8"))

            elif m_type == "BROADCAST_COMPOSITE":
                composite = np.array(msg["composite"], dtype=np.float64)
                dec_bit, norm_val = station.receive_channel_signal(composite)
                resp = json.dumps({
                    "type": "DECODED",
                    "station_id": station_id,
                    "pid": pid,
                    "decoded_bit": dec_bit,
                    "norm": norm_val,
                    "reconstructed_msg": station.receiver.get_message()
                }) + "\n"
                s.sendall(resp.encode("utf-8"))

            elif m_type == "TERMINATE":
                perf, errs, ber = station.verify_reconstruction()
                print(f"\n[Station {station_id} | PID {pid}] Transmission Terminated!")
                print(f"  Sent: '{station.sender.raw_message}' -> Received: '{station.receiver.get_message()}'")
                print(f"  Perfect: {perf} | Errors: {errs} | BER: {ber:.4f}")
                s.close()
                return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CDMA Station Process")
    parser.add_argument("--id", type=int, default=0, help="Station ID (0-indexed)")
    parser.add_argument("--connect", action="store_true", help="Connect to Channel server over TCP socket")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Channel server host")
    parser.add_argument("--port", type=int, default=9000, help="Channel server port")
    parser.add_argument("--msg", type=str, default="STATION_DATA", help="Text payload to transmit")
    args = parser.parse_args()

    if args.connect:
        run_socket_station_client(station_id=args.id, host=args.host, port=args.port, payload=args.msg)
    else:
        print("=== Self-Test: Station, Sender, and Receiver ===")
        from walsh import WalshCodeGenerator
        H, N = WalshCodeGenerator.get_walsh_set(2)
        s0 = Station(0, H[0])
        s1 = Station(1, H[1])
        s0.load_payload([1, 0, 1])
        s1.load_payload([0, 1, 1])
        for slot in range(3):
            c0 = s0.produce_chips()
            c1 = s1.produce_chips()
            composite = c0 + c1
            bit0, norm0 = s0.receive_channel_signal(composite)
            bit1, norm1 = s1.receive_channel_signal(composite)
            print(f"Slot {slot}: C = {composite} | S0 decoded = {bit0} | S1 decoded = {bit1}")
        perf0, err0, ber0 = s0.verify_reconstruction()
        perf1, err1, ber1 = s1.verify_reconstruction()
        print(f"Station 0 Perfect: {perf0} | Station 1 Perfect: {perf1}")
