"""
receiver.py
===========
Receiver program for Assignment 2 — Data Link Layer Simulation.

Implements all three ARQ protocols:
  --protocol saw   : Stop-and-Wait   (receiver window = 1)
  --protocol gbn   : Go-Back-N       (receiver window = 1, in-order only)
  --protocol sr    : Selective Repeat (receiver window = N, buffered)

Run:
    python3 receiver.py [options]

Options:
    --protocol  {saw,gbn,sr}     Flow control protocol    (default: saw)
    --window    N                Receiver window size      (default: 4, SAW ignored)
    --host      HOST             Bind address              (default: 127.0.0.1)
    --port      PORT             TCP port to listen on     (default: 5001)
    --output    FILE             Write received data here  (default: output.txt)
    --payload   SIZE             Payload bytes per frame   (default: 46)
    --verbose                    Print per-frame details
    --dashboard                  Enable rich terminal dashboard
"""

import argparse
import socket
import struct
import time
import os

from channel    import Channel, create_server_socket
from frame      import (parse_frame, check_frame, build_frame,
                        HEADER_SIZE, FCS_SIZE, MAC_SRC, MAC_DST)
from dashboard  import Dashboard, NullDashboard

# ---------------------------------------------------------------------------
# ACK / NAK helpers
# ---------------------------------------------------------------------------

ACK_FLAG = 0x01
NAK_FLAG = 0x00

def _make_ack(seq_no: int) -> bytes:
    """2-byte ACK packet: [0x01, seq_no]"""
    return bytes([ACK_FLAG, seq_no & 0xFF])

def _make_nak(seq_no: int) -> bytes:
    """2-byte NAK packet: [0x00, seq_no]"""
    return bytes([NAK_FLAG, seq_no & 0xFF])

def _send_ack(ch: Channel, seq_no: int, dash=None) -> None:
    ch.transmit(_make_ack(seq_no))
    if dash:
        dash.recv_ack_sent()

def _send_nak(ch: Channel, seq_no: int, dash=None) -> None:
    ch.transmit(_make_nak(seq_no))
    if dash:
        dash.recv_nak_sent()

# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------

def _log(verbose: bool, dash, *args, style="white") -> None:
    msg = " ".join(str(a) for a in args)
    if verbose:
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] [RECEIVER] {msg}", flush=True)
    if dash:
        dash.log(msg, style=style)

# ---------------------------------------------------------------------------
# Stop-and-Wait Receiver
# ---------------------------------------------------------------------------

def run_saw_receiver(ch: Channel, payload_size: int,
                     verbose: bool, dash) -> list[bytes]:
    expected_seq = 0
    received_data: list[bytes] = []
    frame_count = 0
    last_acked_seq = -1

    print("[RECEIVER][SAW] Ready. Waiting for frames ...")
    dash.start()

    while True:
        raw = ch.receive()
        if raw is None:
            print("[RECEIVER][SAW] Connection closed. Done.")
            break

        dash.recv_frame(accepted=False)  # We'll override if accepted

        if not check_frame(raw, payload_size):
            _log(verbose, dash, f"frame received — FCS FAIL → discarded (no ACK)", style="red")
            continue

        frame = parse_frame(raw, payload_size)
        seq   = frame["seq_no"]
        dash.recv_frame(accepted=True)
        _log(verbose, dash, f"Frame seq={seq} received — FCS OK", style="cyan")

        if seq == expected_seq:
            received_data.append(frame["data"])
            _send_ack(ch, seq, dash)
            last_acked_seq = seq
            frame_count += 1
            dash.recv_buffer_update(0, expected_seq)
            _log(verbose, dash, f"Accepted seq={seq} → sent ACK {seq}", style="green")
            expected_seq = 1 - expected_seq
        else:
            if last_acked_seq >= 0:
                _send_ack(ch, last_acked_seq, dash)
                _log(verbose, dash, f"Duplicate seq={seq}, re-sent ACK {last_acked_seq}", style="yellow")

    dash.stop()
    print(f"[RECEIVER][SAW] Received {frame_count} frames ({sum(len(d) for d in received_data)} bytes data)")
    return received_data


# ---------------------------------------------------------------------------
# Go-Back-N Receiver
# ---------------------------------------------------------------------------

def run_gbn_receiver(ch: Channel, payload_size: int,
                     verbose: bool, dash) -> list[bytes]:
    expected_seq  = 0
    received_data: list[bytes] = []
    frame_count   = 0
    last_good_seq = -1

    print("[RECEIVER][GBN] Ready. Waiting for frames ...")
    dash.start()

    while True:
        raw = ch.receive()
        if raw is None:
            print("[RECEIVER][GBN] Connection closed. Done.")
            break

        dash.recv_frame(accepted=False)

        if not check_frame(raw, payload_size):
            _log(verbose, dash, f"Frame received — FCS FAIL → discarded", style="red")
            if last_good_seq >= 0:
                _send_ack(ch, last_good_seq, dash)
            continue

        frame = parse_frame(raw, payload_size)
        seq   = frame["seq_no"]
        dash.recv_frame(accepted=True)

        if seq == expected_seq:
            received_data.append(frame["data"])
            _send_ack(ch, seq, dash)
            last_good_seq = seq
            frame_count  += 1
            dash.recv_buffer_update(0, expected_seq)
            _log(verbose, dash, f"Accepted seq={seq} → cumulative ACK {seq}", style="green")
            expected_seq = (expected_seq + 1) % 256
        else:
            _log(verbose, dash, f"Out-of-order seq={seq} (expected {expected_seq}) → discarded", style="yellow")
            if last_good_seq >= 0:
                _send_ack(ch, last_good_seq, dash)

    dash.stop()
    print(f"[RECEIVER][GBN] Received {frame_count} frames ({sum(len(d) for d in received_data)} bytes data)")
    return received_data


# ---------------------------------------------------------------------------
# Selective Repeat Receiver
# ---------------------------------------------------------------------------

def run_sr_receiver(ch: Channel, payload_size: int,
                    window_size: int, verbose: bool, dash) -> list[bytes]:
    recv_base     = 0
    recv_buffer: dict[int, bytes] = {}
    received_data: list[bytes]    = []
    frame_count   = 0

    print(f"[RECEIVER][SR]  Ready (window={window_size}). Waiting for frames ...")
    dash.start()

    while True:
        raw = ch.receive()
        if raw is None:
            print("[RECEIVER][SR] Connection closed. Done.")
            break

        dash.recv_frame(accepted=False)

        if not check_frame(raw, payload_size):
            frame_bad = parse_frame(raw, payload_size)
            if frame_bad is not None:
                _send_nak(ch, frame_bad["seq_no"], dash)
                _log(verbose, dash, f"FCS FAIL seq={frame_bad['seq_no']} → sent NAK", style="red")
            else:
                _log(verbose, dash, f"FCS FAIL (unparseable) → discarded", style="red")
            continue

        frame = parse_frame(raw, payload_size)
        seq   = frame["seq_no"]
        dash.recv_frame(accepted=True)

        in_window = ((seq - recv_base) % 256 < window_size)
        already_acked = ((recv_base - seq) % 256 <= window_size and seq != recv_base)

        if in_window and seq not in recv_buffer:
            recv_buffer[seq] = frame["data"]
            _send_ack(ch, seq, dash)
            frame_count += 1
            dash.recv_buffer_update(len(recv_buffer), recv_base)
            _log(verbose, dash, f"Buffered seq={seq} → independent ACK {seq}", style="green")

            while recv_base in recv_buffer:
                received_data.append(recv_buffer.pop(recv_base))
                _log(verbose, dash, f"Delivered seq={recv_base} to application", style="cyan")
                recv_base = (recv_base + 1) % 256
            dash.recv_buffer_update(len(recv_buffer), recv_base)

        elif seq in recv_buffer or already_acked:
            _send_ack(ch, seq, dash)
            _log(verbose, dash, f"Duplicate seq={seq} → re-ACK {seq}", style="yellow")
        else:
            _log(verbose, dash, f"seq={seq} outside window (base={recv_base}) → discarded", style="dim white")

    dash.stop()
    print(f"[RECEIVER][SR]  Received {frame_count} frames ({sum(len(d) for d in received_data)} bytes data)")
    return received_data


# ---------------------------------------------------------------------------
# Save received data to file
# ---------------------------------------------------------------------------

def save_output(data_chunks: list[bytes], filepath: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "wb") as f:
        for chunk in data_chunks:
            f.write(chunk)
    total = sum(len(c) for c in data_chunks)
    print(f"[RECEIVER] Output written to '{filepath}' ({total} bytes, {len(data_chunks)} chunks)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assignment 2 — Data Link Layer Receiver",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--protocol", choices=["saw", "gbn", "sr"], default="saw")
    parser.add_argument("--window",   type=int,   default=4)
    parser.add_argument("--host",     default="127.0.0.1")
    parser.add_argument("--port",     type=int,   default=5001)
    parser.add_argument("--output",   default="output.txt")
    parser.add_argument("--payload",  type=int,   default=46)
    parser.add_argument("--verbose",  action="store_true")
    parser.add_argument("--dashboard", action="store_true", help="Enable rich dashboard")
    args = parser.parse_args()

    srv_sock = create_server_socket(args.host, args.port)
    conn, addr = srv_sock.accept()
    print(f"[RECEIVER] Connection from {addr[0]}:{addr[1]}")
    srv_sock.close()

    ch = Channel(conn, p_error=0.0, p_loss=0.0, max_delay_ms=0, label="RECEIVER")

    if args.dashboard:
        dash = Dashboard(protocol=args.protocol, window_size=args.window, 
                         total_frames=100, host=args.host, 
                         port=args.port, role="RECEIVER")
    else:
        dash = NullDashboard()

    start_time = time.time()

    proto = args.protocol
    if proto == "saw":
        data = run_saw_receiver(ch, args.payload, args.verbose, dash)
    elif proto == "gbn":
        data = run_gbn_receiver(ch, args.payload, args.verbose, dash)
    else:
        data = run_sr_receiver(ch, args.payload, args.window, args.verbose, dash)

    elapsed = time.time() - start_time

    save_output(data, args.output)

    total_bytes = sum(len(d) for d in data)
    throughput  = total_bytes / elapsed if elapsed > 0 else 0
    print(f"\n[RECEIVER] ---- Summary ----")
    print(f"  Protocol        : {proto.upper()}")
    print(f"  Total time      : {elapsed:.3f} s")
    print(f"  Data received   : {total_bytes} bytes")
    print(f"  Throughput      : {throughput:.1f} B/s")

    conn.close()

if __name__ == "__main__":
    main()
