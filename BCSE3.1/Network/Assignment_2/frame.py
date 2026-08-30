"""
frame.py
========
Framing module for Assignment 2 — Data Link Layer Simulation.

Frame structure (Ethernet-like):
    +------------------+------------------+-----------+-----------+------------+
    | Src MAC (6 B)    | Dst MAC (6 B)    | Len (2 B) | Seq # (1B)| Payload    |
    +------------------+------------------+-----------+-----------+(46-1500 B) |
    | <----------- HEADER  (15 bytes) ----------------->          |            |
    +-------------------------------------------------------------------+------+
    | FCS — CRC-32 of (header + payload)                         (4 B)  |
    +-----------------------------------------------------------------------+

Key constants (all configurable at module level):
    PAYLOAD_SIZE : fixed payload chunk size in bytes (default 46 — Ethernet minimum)
    MAC_SRC      : sender MAC address string  "XX:XX:XX:XX:XX:XX"
    MAC_DST      : receiver MAC address string

Public API:
    build_frame(seq_no, payload)        -> bytes
    parse_frame(raw_bytes)              -> dict | None
    check_frame(raw_bytes)              -> bool
    read_file_chunks(path, chunk_size)  -> Generator[bytes, None, None]
    split_data_into_frames(data, ...)   -> list[bytes]

Requires:
    error_detection.py  (compute_crc, fcs_to_bytes, bytes_to_fcs, verify_crc)
"""

from __future__ import annotations

import struct
import os
from typing import Generator

from error_detection import compute_crc, verify_crc, fcs_to_bytes, bytes_to_fcs

# ---------------------------------------------------------------------------
# Frame constants — tweak here to change the whole simulation
# ---------------------------------------------------------------------------

PAYLOAD_SIZE: int = 46            # bytes per payload chunk (46–1500)
MAC_SRC: str      = "AA:BB:CC:DD:EE:01"   # sender NIC address
MAC_DST: str      = "AA:BB:CC:DD:EE:02"   # receiver NIC address

# Derived sizes (do not change these)
MAC_SIZE     = 6    # bytes per MAC address
LEN_SIZE     = 2    # bytes for length field (big-endian uint16)
SEQ_SIZE     = 1    # bytes for sequence number (uint8, wraps at 256)
HEADER_SIZE  = MAC_SIZE * 2 + LEN_SIZE + SEQ_SIZE   # = 15 bytes
FCS_SIZE     = 4    # bytes for CRC-32 FCS

# CRC-32 polynomial used for FCS (standard Ethernet / ISO 3309)
CRC_POLY   = 0x04C11DB7
CRC_BITS   = 32

# Ethernet payload bounds (informational; PAYLOAD_SIZE must be in this range)
ETH_MIN_PAYLOAD = 46
ETH_MAX_PAYLOAD = 1500


# ---------------------------------------------------------------------------
# MAC address helpers
# ---------------------------------------------------------------------------

def _mac_to_bytes(mac: str) -> bytes:
    """
    Convert a colon-separated MAC string to 6 raw bytes.

    Example:
        "AA:BB:CC:DD:EE:FF"  ->  b'\\xAA\\xBB\\xCC\\xDD\\xEE\\xFF'

    Raises ValueError if the format is wrong.
    """
    parts = mac.strip().split(":")
    if len(parts) != 6:
        raise ValueError(f"Invalid MAC address: {mac!r}  (expected XX:XX:XX:XX:XX:XX)")
    return bytes(int(p, 16) for p in parts)


def _bytes_to_mac(raw: bytes | bytearray) -> str:
    """Convert 6 raw bytes back to a colon-separated MAC string."""
    return ":".join(f"{b:02X}" for b in raw[:6])


# ---------------------------------------------------------------------------
# build_frame
# ---------------------------------------------------------------------------

def build_frame(seq_no: int,
                payload: bytes | bytearray,
                mac_src: str = MAC_SRC,
                mac_dst: str = MAC_DST,
                payload_size: int = PAYLOAD_SIZE) -> bytes:
    """
    Assemble one complete data frame from a payload chunk.

    Steps:
        1. Pad (or truncate) *payload* to exactly *payload_size* bytes.
        2. Build the 15-byte header:
               src_mac (6) | dst_mac (6) | length (2 BE) | seq_no (1)
        3. Compute CRC-32 over (header + padded_payload).
        4. Append 4-byte big-endian FCS.

    Parameters
    ----------
    seq_no       : int        — frame sequence number (0–255, wraps automatically)
    payload      : bytes      — raw data chunk (will be padded/truncated to payload_size)
    mac_src      : str        — source MAC "XX:XX:XX:XX:XX:XX"
    mac_dst      : str        — destination MAC "XX:XX:XX:XX:XX:XX"
    payload_size : int        — fixed payload slot size in bytes

    Returns
    -------
    bytes — complete frame (HEADER_SIZE + payload_size + FCS_SIZE bytes)

    Raises
    ------
    ValueError — if seq_no is outside [0, 255] or payload_size is invalid
    """
    if not (0 <= seq_no <= 255):
        raise ValueError(f"seq_no must be 0–255, got {seq_no}")
    if not (ETH_MIN_PAYLOAD <= payload_size <= ETH_MAX_PAYLOAD):
        raise ValueError(
            f"payload_size must be {ETH_MIN_PAYLOAD}–{ETH_MAX_PAYLOAD}, got {payload_size}"
        )

    # --- Step 1: pad/truncate payload to fixed size ---
    actual_len = len(payload)
    if actual_len < payload_size:
        padded_payload = bytes(payload) + b'\x00' * (payload_size - actual_len)
    else:
        padded_payload = bytes(payload[:payload_size])
        actual_len = payload_size

    # Clamp the stored length to actual data (before padding), max payload_size
    stored_len = min(len(payload), payload_size)

    # --- Step 2: build header ---
    src_bytes = _mac_to_bytes(mac_src)                      # 6 bytes
    dst_bytes = _mac_to_bytes(mac_dst)                      # 6 bytes
    len_bytes = struct.pack(">H", stored_len)               # 2 bytes big-endian
    seq_byte  = struct.pack("B", seq_no & 0xFF)             # 1 byte

    header = src_bytes + dst_bytes + len_bytes + seq_byte   # 15 bytes

    # --- Step 3: compute CRC-32 FCS over header + padded payload ---
    protected = header + padded_payload
    crc_value = compute_crc(protected, poly=CRC_POLY, bit_len=CRC_BITS)
    fcs = fcs_to_bytes(crc_value)                           # 4 bytes

    # --- Step 4: assemble final frame ---
    return protected + fcs


# ---------------------------------------------------------------------------
# parse_frame
# ---------------------------------------------------------------------------

def parse_frame(raw_bytes: bytes | bytearray,
                payload_size: int = PAYLOAD_SIZE) -> dict | None:
    """
    Deserialise a raw byte string back into its frame fields.

    The returned dictionary has these keys:
        "mac_src"   : str   — source MAC  "XX:XX:XX:XX:XX:XX"
        "mac_dst"   : str   — destination MAC
        "length"    : int   — stored payload length (before padding)
        "seq_no"    : int   — sequence number (0–255)
        "payload"   : bytes — padded payload (payload_size bytes)
        "data"      : bytes — actual data bytes (payload[:length])
        "fcs"       : int   — received FCS (32-bit integer)
        "raw"       : bytes — the complete raw frame

    Returns None if the frame is too short to parse.

    Parameters
    ----------
    raw_bytes    : bytes or bytearray — the raw received frame
    payload_size : int                — expected payload slot size

    Returns
    -------
    dict | None
    """
    min_frame_size = HEADER_SIZE + payload_size + FCS_SIZE
    if len(raw_bytes) < min_frame_size:
        return None   # frame is malformed / too short to parse

    raw = bytes(raw_bytes)

    # --- Header fields ---
    mac_src_raw = raw[0:6]
    mac_dst_raw = raw[6:12]
    length,     = struct.unpack(">H", raw[12:14])   # big-endian uint16
    seq_no      = raw[14]                            # uint8

    # --- Payload ---
    payload = raw[15 : 15 + payload_size]            # padded slot
    data    = payload[:length]                       # actual data bytes

    # --- FCS ---
    fcs_raw = raw[15 + payload_size : 15 + payload_size + FCS_SIZE]
    fcs_val = bytes_to_fcs(fcs_raw)

    return {
        "mac_src": _bytes_to_mac(mac_src_raw),
        "mac_dst": _bytes_to_mac(mac_dst_raw),
        "length":  length,
        "seq_no":  seq_no,
        "payload": payload,
        "data":    data,
        "fcs":     fcs_val,
        "raw":     raw,
    }


# ---------------------------------------------------------------------------
# check_frame  (called Check() in the assignment spec)
# ---------------------------------------------------------------------------

def check_frame(raw_bytes: bytes | bytearray,
                payload_size: int = PAYLOAD_SIZE) -> bool:
    """
    Verify the frame's FCS integrity using CRC-32.

    The CRC was computed over (header + padded_payload) during build_frame.
    We re-extract that region and recompute — if the result matches the
    stored FCS, the frame is intact.

    Parameters
    ----------
    raw_bytes    : bytes or bytearray — the raw received frame
    payload_size : int                — expected payload slot size

    Returns
    -------
    True  — frame is intact (FCS matches)
    False — frame is corrupted  (FCS mismatch) or too short
    """
    frame = parse_frame(raw_bytes, payload_size)
    if frame is None:
        return False   # too short to even parse

    # Re-derive the protected region (same bytes that were CRC'd at the sender)
    protected = frame["raw"][:HEADER_SIZE + payload_size]
    return verify_crc(protected, frame["fcs"], poly=CRC_POLY, bit_len=CRC_BITS)


# ---------------------------------------------------------------------------
# read_file_chunks
# ---------------------------------------------------------------------------

def read_file_chunks(filepath: str,
                     chunk_size: int = PAYLOAD_SIZE) -> Generator[bytes, None, None]:
    """
    Generator that yields fixed-size byte chunks from a file.

    The last chunk is zero-padded if the file size is not an exact multiple
    of *chunk_size*.

    Parameters
    ----------
    filepath   : str — path to the input file
    chunk_size : int — bytes per chunk (must be 46–1500)

    Yields
    ------
    bytes — chunks of exactly *chunk_size* bytes

    Raises
    ------
    FileNotFoundError — if the file does not exist
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Input file not found: {filepath!r}")

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break                           # EOF
            if len(chunk) < chunk_size:
                chunk = chunk + b'\x00' * (chunk_size - len(chunk))   # pad last chunk
            yield chunk


# ---------------------------------------------------------------------------
# split_data_into_frames  (convenience — builds all frames from a file)
# ---------------------------------------------------------------------------

def split_data_into_frames(filepath: str,
                           payload_size: int = PAYLOAD_SIZE,
                           mac_src: str = MAC_SRC,
                           mac_dst: str = MAC_DST) -> list[bytes]:
    """
    Read an entire file and return a list of complete, ready-to-send frames.

    Sequence numbers are assigned starting from 0 and wrap at 256.

    Parameters
    ----------
    filepath     : str — path to the input text file
    payload_size : int — chunk size per frame (46–1500)
    mac_src      : str — source MAC address
    mac_dst      : str — destination MAC address

    Returns
    -------
    list[bytes] — ordered list of frame byte strings
    """
    frames = []
    for seq_no, chunk in enumerate(read_file_chunks(filepath, payload_size)):
        frame = build_frame(
            seq_no    = seq_no % 256,
            payload   = chunk,
            mac_src   = mac_src,
            mac_dst   = mac_dst,
            payload_size = payload_size,
        )
        frames.append(frame)
    return frames


# ---------------------------------------------------------------------------
# Pretty-print helper
# ---------------------------------------------------------------------------

def frame_info(raw_bytes: bytes | bytearray,
               payload_size: int = PAYLOAD_SIZE) -> str:
    """
    Return a human-readable summary string for a frame.
    Useful for logging in the Sender/Receiver programs.

    Example output:
        [Frame] seq=3  src=AA:BB:CC:DD:EE:01  dst=AA:BB:CC:DD:EE:02
                len=46  fcs=0x1A2B3C4D  size=65B  integrity=OK
    """
    frame = parse_frame(raw_bytes, payload_size)
    if frame is None:
        return "[Frame] <too short to parse>"
    intact = check_frame(raw_bytes, payload_size)
    total  = len(raw_bytes)
    return (
        f"[Frame] seq={frame['seq_no']:<3}  "
        f"src={frame['mac_src']}  dst={frame['mac_dst']}\n"
        f"        len={frame['length']}B  "
        f"fcs=0x{frame['fcs']:08X}  "
        f"total={total}B  "
        f"integrity={'OK' if intact else 'CORRUPTED'}"
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("frame.py — self-test")
    print("=" * 60)

    # --- 1. Build a frame from sample text ---
    sample_payload = b"Hello, DataLink Layer! This is frame 0."
    frame_bytes = build_frame(seq_no=0, payload=sample_payload)

    total_expected = HEADER_SIZE + PAYLOAD_SIZE + FCS_SIZE
    print(f"\n[1] build_frame(seq=0)")
    print(f"    payload input  : {sample_payload!r}")
    print(f"    frame size     : {len(frame_bytes)} bytes  (expected {total_expected})")
    print(f"    frame hex      : {frame_bytes[:20].hex(' ')} ...")

    # --- 2. Parse it back ---
    parsed = parse_frame(frame_bytes)
    print(f"\n[2] parse_frame()")
    print(f"    mac_src  : {parsed['mac_src']}")
    print(f"    mac_dst  : {parsed['mac_dst']}")
    print(f"    seq_no   : {parsed['seq_no']}")
    print(f"    length   : {parsed['length']}")
    print(f"    data     : {parsed['data']!r}")
    print(f"    fcs      : 0x{parsed['fcs']:08X}")

    # --- 3. Check integrity (should pass) ---
    ok = check_frame(frame_bytes)
    print(f"\n[3] check_frame() on clean frame  -> {'PASS ✓' if ok else 'FAIL ✗'}")

    # --- 4. Corrupt a byte and check again ---
    corrupted = bytearray(frame_bytes)
    corrupted[16] ^= 0xFF   # flip all bits in first payload byte
    corrupted = bytes(corrupted)
    ok_corrupted = check_frame(corrupted)
    print(f"[4] check_frame() on corrupted    -> {'PASS' if ok_corrupted else 'FAIL ✗ (expected)'}")

    # --- 5. Pretty print ---
    print(f"\n[5] frame_info():")
    print("   ", frame_info(frame_bytes))

    # --- 6. File chunking (create a small temp file) ---
    import tempfile
    test_text = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" * 10   # 360 bytes
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(test_text)
        tmp_path = tmp.name

    chunks = list(read_file_chunks(tmp_path, chunk_size=PAYLOAD_SIZE))
    os.unlink(tmp_path)
    expected_chunks = -(-len(test_text) // PAYLOAD_SIZE)   # ceiling division
    print(f"\n[6] read_file_chunks(): {len(chunks)} chunks  (expected {expected_chunks})")
    print(f"    last chunk length : {len(chunks[-1])} bytes")

    # --- 7. split_data_into_frames round-trip ---
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(test_text)
        tmp_path = tmp.name

    all_frames = split_data_into_frames(tmp_path)
    os.unlink(tmp_path)
    print(f"\n[7] split_data_into_frames(): {len(all_frames)} frames built")
    all_ok = all(check_frame(f) for f in all_frames)
    print(f"    All frames pass integrity check: {'YES ✓' if all_ok else 'NO ✗'}")

    print("\n" + "=" * 60)
    print("Self-test complete.")
