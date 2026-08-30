"""
channel.py
==========
Simulates a noisy, lossy network channel between Sender and Receiver.

The Channel() method from the assignment spec is implemented here as a
class.  It wraps a raw TCP socket send/recv and applies, in order:

  1. Frame loss  — with probability p_loss, the frame is silently dropped
                   (transmit() returns None and nothing goes on the wire).
  2. Random delay — a uniform delay in [0, max_delay_ms] ms is slept before
                    the data is put on the socket.  A large delay will cause
                    the sender's timer to expire, simulating "timeout loss".
  3. Bit error   — with probability p_error the frame bytes are corrupted
                   using introduce_random_bit_flip from error_injection.py.

Usage (sender side):
    ch = Channel(sock, p_error=0.1, p_loss=0.1, max_delay_ms=50)
    sent = ch.transmit(frame_bytes)     # returns True if actually sent

Usage (receiver side):
    ch = Channel(sock, ...)
    raw = ch.receive(frame_size)        # returns bytes or None on loss/error
"""

import socket
import struct
import time
import random

from error_injection import introduce_random_bit_flip


# Wire format: every message is prefixed with a 4-byte big-endian length so
# that TCP stream boundaries are preserved.
_LEN_PREFIX = 4   # bytes


class Channel:
    """
    Wraps a connected TCP socket and applies configurable impairments.

    Parameters
    ----------
    sock         : socket.socket — a *connected* TCP socket (blocking mode)
    p_error      : float in [0, 1] — probability of a random-bit-flip error
    p_loss       : float in [0, 1] — probability of silent frame drop
    max_delay_ms : float — upper bound (ms) for uniform random delay
    label        : str   — label for log lines ("SENDER"/"RECEIVER"/"CHANNEL")
    """

    def __init__(self,
                 sock: socket.socket,
                 p_error: float = 0.0,
                 p_loss: float = 0.0,
                 max_delay_ms: float = 50.0,
                 label: str = "CHANNEL",
                 verbose: bool = False):
        self._sock         = sock
        self.p_error       = p_error
        self.p_loss        = p_loss
        self.max_delay_ms  = max_delay_ms
        self.label         = label
        self.verbose       = verbose   # if False, suppresses routine DELAY lines

        # Statistics counters
        self.stats = {
            "sent":        0,
            "dropped":     0,
            "corrupted":   0,
            "delayed":     0,
        }

    # ------------------------------------------------------------------
    # transmit() — called by the Sender to put a frame on the wire
    # ------------------------------------------------------------------

    def transmit(self, frame_bytes: bytes | bytearray) -> bool:
        """
        Apply channel impairments and send *frame_bytes* over the socket.

        Steps (in order, matching the assignment spec):
          1. Loss check  — drop silently with probability p_loss
          2. Delay       — sleep for a random duration
          3. Error       — corrupt a bit with probability p_error
          4. Send        — prefix length + data over TCP

        Returns
        -------
        True  — frame was put on the socket (possibly corrupted)
        False — frame was dropped (simulated loss)
        """
        frame = bytearray(frame_bytes)

        # --- Step 1: Loss ---
        if random.random() < self.p_loss:
            self.stats["dropped"] += 1
            if self.verbose:
                self._log(f"DROP  — frame silently discarded (p_loss={self.p_loss:.2f})")
            return False

        # --- Step 2: Delay ---
        delay_ms = random.uniform(0, self.max_delay_ms)
        if delay_ms > 0:
            self.stats["delayed"] += 1
            if self.verbose:
                self._log(f"DELAY — sleeping {delay_ms:.1f} ms")
            time.sleep(delay_ms / 1000.0)

        # --- Step 3: Bit error ---
        if random.random() < self.p_error:
            frame = introduce_random_bit_flip(frame)
            self.stats["corrupted"] += 1
            if self.verbose:
                self._log(f"ERROR — bit flip injected into frame")

        # --- Step 4: Send (length-prefixed) ---
        self._send_raw(bytes(frame))
        self.stats["sent"] += 1
        return True

    # ------------------------------------------------------------------
    # receive() — called by the Receiver to pull one frame off the wire
    # ------------------------------------------------------------------

    def receive(self) -> bytes | None:
        """
        Read exactly one length-prefixed message from the socket.

        Returns
        -------
        bytes — the raw frame data (possibly corrupted by the channel)
        None  — connection closed or error
        """
        try:
            raw = self._recv_raw()
            return raw
        except (ConnectionResetError, BrokenPipeError, OSError):
            return None

    # ------------------------------------------------------------------
    # Internal send/recv with 4-byte length prefix
    # ------------------------------------------------------------------

    def _send_raw(self, data: bytes) -> None:
        """Send length (4 B big-endian) then data over the socket."""
        length_prefix = struct.pack(">I", len(data))
        self._sock.sendall(length_prefix + data)

    def _recv_raw(self) -> bytes | None:
        """Receive a length-prefixed message from the socket."""
        # Read 4-byte length prefix
        header = self._recv_exactly(_LEN_PREFIX)
        if header is None:
            return None
        msg_len, = struct.unpack(">I", header)

        # Read exactly msg_len bytes
        return self._recv_exactly(msg_len)

    def _recv_exactly(self, n: int) -> bytes | None:
        """Receive exactly *n* bytes, blocking until all arrive or conn closes."""
        buf = b""
        while len(buf) < n:
            try:
                chunk = self._sock.recv(n - len(buf))
            except OSError:
                return None
            if not chunk:
                return None   # connection closed
            buf += chunk
        return buf

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] [{self.label}] {msg}", flush=True)

    def print_stats(self) -> None:
        """Print channel statistics summary."""
        print(f"\n[{self.label}] Channel Statistics:")
        print(f"  Frames sent      : {self.stats['sent']}")
        print(f"  Frames dropped   : {self.stats['dropped']}")
        print(f"  Frames corrupted : {self.stats['corrupted']}")
        print(f"  Frames delayed   : {self.stats['delayed']}")


# ---------------------------------------------------------------------------
# Standalone server/client helpers — used in sender.py / receiver.py
# ---------------------------------------------------------------------------

def create_server_socket(host: str = "127.0.0.1",
                         port: int = 5001,
                         backlog: int = 1) -> socket.socket:
    """
    Create a TCP server socket, bind, and listen.

    Returns the *server* socket (call .accept() to get the connection socket).
    """
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(backlog)
    print(f"[SERVER] Listening on {host}:{port} ...")
    return srv


def create_client_socket(host: str = "127.0.0.1",
                         port: int = 5001,
                         retries: int = 10,
                         retry_delay: float = 0.5) -> socket.socket:
    """
    Create a TCP client socket and connect to *host*:*port*.

    Retries up to *retries* times with *retry_delay* seconds between attempts
    to handle the case where the receiver has not started yet.
    """
    for attempt in range(1, retries + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            print(f"[CLIENT] Connected to {host}:{port}")
            return sock
        except ConnectionRefusedError:
            print(f"[CLIENT] Connection refused (attempt {attempt}/{retries}), retrying...")
            time.sleep(retry_delay)
    raise ConnectionRefusedError(f"Could not connect to {host}:{port} after {retries} attempts")


# ---------------------------------------------------------------------------
# Self-test (loopback — requires two threads)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import threading

    HOST, PORT = "127.0.0.1", 59876
    TEST_DATA  = b"TestFramePayload_" * 4   # 68 bytes

    results: list[bytes] = []

    def _server_thread():
        srv = create_server_socket(HOST, PORT)
        conn, addr = srv.accept()
        ch = Channel(conn, p_error=0.0, p_loss=0.0, max_delay_ms=5, label="SERVER")
        data = ch.receive()
        results.append(data or b"")
        conn.close()
        srv.close()

    t = threading.Thread(target=_server_thread, daemon=True)
    t.start()
    time.sleep(0.2)

    sock = create_client_socket(HOST, PORT)
    ch = Channel(sock, p_error=0.0, p_loss=0.0, max_delay_ms=5, label="CLIENT")
    ch.transmit(TEST_DATA)
    sock.close()
    t.join(timeout=3)

    received = results[0] if results else b""
    print(f"\n[Test] Sent    : {TEST_DATA[:20].hex(' ')} ...")
    print(f"[Test] Received: {received[:20].hex(' ')} ...")
    print(f"[Test] Match   : {'YES ✓' if received == TEST_DATA else 'NO ✗'}")
    ch.print_stats()
