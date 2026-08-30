"""
sender.py
=========
Sender program for Assignment 2 — Data Link Layer Simulation.

Implements all three ARQ protocols:
  --protocol saw   : Stop-and-Wait   (send one, wait for ACK)
  --protocol gbn   : Go-Back-N       (sender window = N, cumulative ACK)
  --protocol sr    : Selective Repeat (sender window = N, independent ACK)

Run:
    python3 sender.py [options]

Options:
    --protocol  {saw,gbn,sr}     Flow control protocol    (default: saw)
    --window    N                Sender window size        (default: 4)
    --host      HOST             Receiver's IP address     (default: 127.0.0.1)
    --port      PORT             Receiver's TCP port       (default: 5001)
    --input     FILE             File to transmit          (default: input.txt)
    --payload   SIZE             Payload bytes per frame   (default: 46)
    --p-error   FLOAT            Bit-error probability     (default: 0.0)
    --p-loss    FLOAT            Frame-loss probability    (default: 0.0)
    --delay     MS               Max channel delay (ms)    (default: 50)
    --timeout   MS               Initial timeout (ms)      (default: 500)
    --verbose                    Print per-frame details
    --dashboard                  Enable rich terminal dashboard
"""

import argparse
import socket
import select
import time
import threading
import os

from channel        import Channel, create_client_socket
from frame          import (build_frame, parse_frame, read_file_chunks,
                            PAYLOAD_SIZE, MAC_SRC, MAC_DST)
from timer          import FrameTimer
from dashboard      import Dashboard, NullDashboard

# ---------------------------------------------------------------------------
# ACK / NAK helpers
# ---------------------------------------------------------------------------

ACK_FLAG = 0x01
NAK_FLAG = 0x00

def _parse_ack(raw: bytes | bytearray) -> tuple[int, int] | None:
    """Parse 2-byte ACK/NAK. Returns (flag, seq_no) or None."""
    if raw is None or len(raw) < 2:
        return None
    return raw[0], raw[1]

# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------

def _log(verbose: bool, dash, *args, style="white") -> None:
    msg = " ".join(str(a) for a in args)
    if verbose:
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] [SENDER] {msg}", flush=True)
    if dash:
        dash.log(msg, style=style)

# ---------------------------------------------------------------------------
# Metrics collector (shared across protocol runs)
# ---------------------------------------------------------------------------

class Metrics:
    def __init__(self):
        self.frames_original     = 0   # frames that carry original data
        self.frames_retransmitted = 0  # retransmit attempts
        self.total_bytes_data    = 0
        self.start_time          = time.time()
        self.end_time            = None

    def stop(self):
        self.end_time = time.time()

    @property
    def elapsed(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time

    @property
    def throughput(self) -> float:
        return self.total_bytes_data / self.elapsed if self.elapsed > 0 else 0

    @property
    def efficiency(self) -> float:
        total = self.frames_original + self.frames_retransmitted
        return self.frames_original / total if total > 0 else 1.0

    def print_summary(self, protocol: str) -> None:
        print(f"\n[SENDER] ---- {protocol.upper()} Summary ----")
        print(f"  Total time         : {self.elapsed:.3f} s")
        print(f"  Original frames    : {self.frames_original}")
        print(f"  Retransmissions    : {self.frames_retransmitted}")
        print(f"  Data bytes sent    : {self.total_bytes_data}")
        print(f"  Throughput         : {self.throughput:.1f} B/s")
        print(f"  Channel efficiency : {self.efficiency * 100:.1f}%")


# ---------------------------------------------------------------------------
# Stop-and-Wait Sender
# ---------------------------------------------------------------------------

def run_saw_sender(ch: Channel, filepath: str, payload_size: int,
                   initial_timeout_ms: float, verbose: bool, dash) -> Metrics:
    timer   = FrameTimer(initial_timeout_ms=initial_timeout_ms)
    metrics = Metrics()
    seq_no  = 0

    print(f"[SENDER][SAW] Starting transmission ...")
    dash.start()

    chunk_idx = 0
    for chunk in read_file_chunks(filepath, payload_size):
        frame = build_frame(seq_no, chunk)
        metrics.frames_original  += 1
        metrics.total_bytes_data += len(chunk)
        dash.update_window(chunk_idx, chunk_idx + 1)
        dash.update_metrics(metrics.frames_original, metrics.frames_retransmitted, metrics.total_bytes_data)

        while True:
            # Transmit
            ch.transmit(frame)
            timer.start(seq_no)
            dash.frame_sent(chunk_idx)
            _log(verbose, dash, f"Sent frame seq={seq_no}", style="cyan")

            # Wait for ACK with timeout
            sock = ch._sock
            timeout_s = timer.timeout_ms / 1000.0
            ready = select.select([sock], [], [], timeout_s)[0]

            if ready:
                raw_ack = ch.receive()
                parsed  = _parse_ack(raw_ack or b"")
                if parsed and parsed[0] == ACK_FLAG and parsed[1] == seq_no:
                    sample_rtt = timer.stop(seq_no)
                    if sample_rtt:
                        timer.update_timeout(sample_rtt)
                        dash.update_rtt(sample_rtt, timer.est_rtt_ms, timer.timeout_ms)
                    dash.frame_acked(chunk_idx)
                    _log(verbose, dash, f"ACK {seq_no} received", style="green")
                    break   # advance to next frame
                else:
                    _log(verbose, dash, f"Bad/wrong ACK, retransmitting seq={seq_no}", style="yellow")
                    metrics.frames_retransmitted += 1
                    dash.frame_retransmit(chunk_idx)
                    dash.update_metrics(metrics.frames_original, metrics.frames_retransmitted, metrics.total_bytes_data)
                    timer.cancel(seq_no)
            else:
                dash.frame_timeout(chunk_idx)
                _log(verbose, dash, f"TIMEOUT on seq={seq_no}, retransmitting", style="bold yellow")
                metrics.frames_retransmitted += 1
                dash.frame_retransmit(chunk_idx)
                dash.update_metrics(metrics.frames_original, metrics.frames_retransmitted, metrics.total_bytes_data)
                timer.cancel(seq_no)

        seq_no = 1 - seq_no   # alternate between 0 and 1
        chunk_idx += 1

    metrics.stop()
    dash.stop()
    print(f"[SENDER][SAW] Transmission complete.")
    timer.print_stats()
    return metrics


# ---------------------------------------------------------------------------
# Go-Back-N Sender
# ---------------------------------------------------------------------------

def run_gbn_sender(ch: Channel, filepath: str, payload_size: int,
                   window_size: int, initial_timeout_ms: float,
                   verbose: bool, dash) -> Metrics:
    timer   = FrameTimer(initial_timeout_ms=initial_timeout_ms)
    metrics = Metrics()

    all_chunks = list(read_file_chunks(filepath, payload_size))
    total      = len(all_chunks)
    all_frames = [build_frame(i % 256, all_chunks[i]) for i in range(total)]
    
    metrics.frames_original  = total
    metrics.total_bytes_data = sum(len(c) for c in all_chunks)
    dash.update_metrics(metrics.frames_original, metrics.frames_retransmitted, metrics.total_bytes_data)

    base     = 0
    next_idx = 0
    lock     = threading.Lock()

    print(f"[SENDER][GBN] Transmitting {total} frames, window={window_size} ...")
    dash.start()

    def ack_receiver_thread():
        nonlocal base
        while base < total:
            raw_ack = ch.receive()
            if raw_ack is None:
                break
            parsed = _parse_ack(raw_ack)
            if parsed and parsed[0] == ACK_FLAG:
                ack_seq = parsed[1]
                with lock:
                    for idx in range(base, next_idx):
                        if idx % 256 == ack_seq:
                            sample_rtt = timer.stop(idx % 256)
                            if sample_rtt:
                                timer.update_timeout(sample_rtt)
                                dash.update_rtt(sample_rtt, timer.est_rtt_ms, timer.timeout_ms)
                            old_base = base
                            base = idx + 1
                            for i in range(old_base, base):
                                dash.frame_acked(i)
                            dash.update_window(base, next_idx)
                            _log(verbose, dash, f"Cumulative ACK {ack_seq}: advanced base {old_base}→{base}", style="green")
                            break

    ack_thread = threading.Thread(target=ack_receiver_thread, daemon=True)
    ack_thread.start()

    while base < total:
        with lock:
            while next_idx < total and next_idx < base + window_size:
                ch.transmit(all_frames[next_idx])
                timer.start(next_idx % 256)
                dash.frame_sent(next_idx)
                dash.update_window(base, next_idx + 1)
                _log(verbose, dash, f"Sent frame idx={next_idx} seq={next_idx % 256}", style="cyan")
                next_idx += 1

            base_seq = base % 256
            if timer.is_expired(base_seq) and base < total:
                dash.frame_timeout(base)
                _log(verbose, dash, f"TIMEOUT on base seq={base_seq}: retransmitting window [{base}..{next_idx-1}]", style="bold yellow")
                for idx in range(base, next_idx):
                    ch.transmit(all_frames[idx])
                    metrics.frames_retransmitted += 1
                    dash.frame_retransmit(idx)
                    timer.start(idx % 256)
                    _log(verbose, dash, f"  Retransmit idx={idx} seq={idx % 256}", style="yellow")
                dash.update_metrics(metrics.frames_original, metrics.frames_retransmitted, metrics.total_bytes_data)

        time.sleep(0.001)

    ack_thread.join(timeout=2.0)
    metrics.stop()
    dash.stop()
    print(f"[SENDER][GBN] Transmission complete.")
    timer.print_stats()
    return metrics


# ---------------------------------------------------------------------------
# Selective Repeat Sender
# ---------------------------------------------------------------------------

def run_sr_sender(ch: Channel, filepath: str, payload_size: int,
                  window_size: int, initial_timeout_ms: float,
                  verbose: bool, dash) -> Metrics:
    timer   = FrameTimer(initial_timeout_ms=initial_timeout_ms)
    metrics = Metrics()

    all_chunks = list(read_file_chunks(filepath, payload_size))
    total      = len(all_chunks)
    all_frames = [build_frame(i % 256, all_chunks[i]) for i in range(total)]
    
    metrics.frames_original  = total
    metrics.total_bytes_data = sum(len(c) for c in all_chunks)
    dash.update_metrics(metrics.frames_original, metrics.frames_retransmitted, metrics.total_bytes_data)

    base       = 0
    next_idx   = 0
    acked      = set()
    lock       = threading.Lock()

    print(f"[SENDER][SR] Transmitting {total} frames, window={window_size} ...")
    dash.start()

    def ack_receiver_thread():
        nonlocal base
        while base < total:
            raw_ack = ch.receive()
            if raw_ack is None:
                break
            parsed = _parse_ack(raw_ack)
            if not parsed:
                continue
            flag, seq = parsed

            with lock:
                if flag == 0x01:   # ACK
                    for idx in range(base, next_idx):
                        if idx % 256 == seq and idx not in acked:
                            sample_rtt = timer.stop(seq)
                            if sample_rtt:
                                timer.update_timeout(sample_rtt)
                                dash.update_rtt(sample_rtt, timer.est_rtt_ms, timer.timeout_ms)
                            acked.add(idx)
                            dash.frame_acked(idx)
                            _log(verbose, dash, f"ACK {seq} (idx={idx})", style="green")
                            break

                    while base in acked:
                        acked.discard(base)
                        base += 1
                    dash.update_window(base, next_idx)

                elif flag == 0x00:  # NAK
                    for idx in range(base, next_idx):
                        if idx % 256 == seq and idx not in acked:
                            ch.transmit(all_frames[idx])
                            timer.start(seq)
                            metrics.frames_retransmitted += 1
                            dash.frame_retransmit(idx)
                            dash.update_metrics(metrics.frames_original, metrics.frames_retransmitted, metrics.total_bytes_data)
                            _log(verbose, dash, f"NAK {seq}: immediate retransmit idx={idx}", style="yellow")
                            break

    ack_thread = threading.Thread(target=ack_receiver_thread, daemon=True)
    ack_thread.start()

    while base < total:
        with lock:
            while next_idx < total and next_idx < base + window_size:
                ch.transmit(all_frames[next_idx])
                timer.start(next_idx % 256)
                dash.frame_sent(next_idx)
                dash.update_window(base, next_idx + 1)
                _log(verbose, dash, f"Sent idx={next_idx} seq={next_idx % 256}", style="cyan")
                next_idx += 1

            for idx in range(base, next_idx):
                if idx in acked:
                    continue
                seq = idx % 256
                if timer.is_expired(seq):
                    dash.frame_timeout(idx)
                    ch.transmit(all_frames[idx])
                    timer.start(seq)
                    metrics.frames_retransmitted += 1
                    dash.frame_retransmit(idx)
                    dash.update_metrics(metrics.frames_original, metrics.frames_retransmitted, metrics.total_bytes_data)
                    _log(verbose, dash, f"TIMEOUT idx={idx} seq={seq}: selective retransmit", style="bold yellow")

        time.sleep(0.001)

    ack_thread.join(timeout=2.0)
    metrics.stop()
    dash.stop()
    print(f"[SENDER][SR] Transmission complete.")
    timer.print_stats()
    return metrics


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assignment 2 — Data Link Layer Sender",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--protocol", choices=["saw", "gbn", "sr"], default="saw")
    parser.add_argument("--window",   type=int,   default=4)
    parser.add_argument("--host",     default="127.0.0.1")
    parser.add_argument("--port",     type=int,   default=5001)
    parser.add_argument("--input",    default="input.txt")
    parser.add_argument("--payload",  type=int,   default=46)
    parser.add_argument("--p-error",  type=float, default=0.0, dest="p_error")
    parser.add_argument("--p-loss",   type=float, default=0.0, dest="p_loss")
    parser.add_argument("--delay",    type=float, default=50.0)
    parser.add_argument("--timeout",  type=float, default=500.0)
    parser.add_argument("--verbose",  action="store_true")
    parser.add_argument("--dashboard", action="store_true", help="Enable rich dashboard")
    args = parser.parse_args()

    sock = create_client_socket(args.host, args.port)
    ch   = Channel(sock, p_error=args.p_error, p_loss=args.p_loss,
                   max_delay_ms=args.delay, label="SENDER")

    if args.dashboard:
        try:
            total_size = os.path.getsize(args.input)
            total_frames_est = max(1, (total_size + args.payload - 1) // args.payload)
        except Exception:
            total_frames_est = 100
        dash = Dashboard(protocol=args.protocol, window_size=args.window, 
                         total_frames=total_frames_est, host=args.host, 
                         port=args.port, role="SENDER")
    else:
        dash = NullDashboard()

    proto = args.protocol
    if proto == "saw":
        m = run_saw_sender(ch, args.input, args.payload, args.timeout, args.verbose, dash)
    elif proto == "gbn":
        m = run_gbn_sender(ch, args.input, args.payload, args.window, args.timeout, args.verbose, dash)
    else:
        m = run_sr_sender(ch, args.input, args.payload, args.window, args.timeout, args.verbose, dash)

    m.print_summary(proto)
    ch.print_stats()
    sock.close()


if __name__ == "__main__":
    main()
