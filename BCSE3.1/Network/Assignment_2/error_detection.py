"""
error_detection.py
==================
Python port of ErrorDetection.cpp (Assignment 1).

Provides two error-detection schemes:
  1. Internet Checksum  (RFC 1071)  -> 16-bit result
  2. CRC (shift-register method)   -> variable-width result (use 32-bit for FCS)

Both functions operate on plain bytes / bytearray objects.

Typical usage for frame FCS (CRC-32 with poly 0x04C11DB7, bitLen=32):
    from error_detection import compute_crc
    fcs = compute_crc(header + payload, poly=0x04C11DB7, bit_len=32)

For checksum:
    from error_detection import compute_checksum
    cs  = compute_checksum(header + payload)
"""

# ---------------------------------------------------------------------------
# Internet Checksum  (mirrors computeInternetChecksum in ErrorDetection.cpp)
# ---------------------------------------------------------------------------

def compute_checksum(data: bytes | bytearray) -> int:
    """
    RFC 1071 Internet Checksum.

    Treats *data* as a sequence of 16-bit big-endian words, sums them in
    one's-complement arithmetic, and returns the one's-complement of the sum
    as a 16-bit integer.

    If the data length is odd, the last byte is padded with a zero byte on
    the right (high byte = data byte, low byte = 0x00), exactly as in the
    original C++ implementation.

    Parameters
    ----------
    data : bytes or bytearray
        The payload to protect.

    Returns
    -------
    int
        16-bit checksum value (0x0000–0xFFFF).
    """
    acc: int = 0
    length: int = len(data)
    index: int = 0

    # Sum 16-bit big-endian words
    while length > 1:
        chunk = (data[index] << 8) | data[index + 1]
        acc += chunk
        index += 2
        length -= 2

    # Odd trailing byte — pad low side with 0x00 (matches C++ payload.back() << 8)
    if length > 0:
        chunk = (data[index] << 8) | 0x00
        acc += chunk

    # Fold 32-bit accumulator into 16 bits (one's-complement carry-around)
    while acc >> 16:
        acc = (acc & 0xFFFF) + (acc >> 16)

    return (~acc) & 0xFFFF


def verify_checksum(data: bytes | bytearray, received_checksum: int) -> bool:
    """
    Return True if *data* is intact given *received_checksum*.

    The standard property of the Internet Checksum is:
        compute_checksum(data + checksum_bytes) == 0xFFFF
    We implement it by recomputing and comparing directly.
    """
    return compute_checksum(data) == received_checksum


# ---------------------------------------------------------------------------
# CRC — shift-register (mirrors computeCyclicRedundancy in ErrorDetection.cpp)
# ---------------------------------------------------------------------------

def compute_crc(data: bytes | bytearray, poly: int = 0x04C11DB7, bit_len: int = 32) -> int:
    """
    CRC computation using a software shift-register, ported 1-to-1 from the
    C++ implementation in ErrorDetection.cpp.

    The algorithm:
      1. Processes each byte MSB-first.
      2. Feeds each bit into a *bit_len*-wide shift register.
      3. XORs with *poly* whenever the register's MSB was 1 before the shift.
      4. After all data bits, flushes *bit_len* zero-bits (equivalent to
         appending r zero-bits before division).
      5. Masks the result to *bit_len* bits.

    Parameters
    ----------
    data    : bytes or bytearray   — payload to protect
    poly    : int                  — generator polynomial (default CRC-32)
    bit_len : int                  — CRC width in bits (8, 16, or 32)

    Returns
    -------
    int
        CRC value, *bit_len* bits wide.

    Common polynomials
    ------------------
    CRC-32  : poly=0x04C11DB7, bit_len=32   (Ethernet FCS)
    CRC-16  : poly=0x8005,     bit_len=16
    CRC-8   : poly=0x1D5,      bit_len=8    (see CRC-8 collision in ErrorInjection)
    """
    if bit_len == 32:
        boundary: int = 0xFFFFFFFF
    else:
        boundary = (1 << bit_len) - 1

    register_val: int = 0

    # --- Phase 1: process data bytes (MSB first) ---
    for byte in data:
        for b in range(7, -1, -1):
            extracted_bit = (byte >> b) & 1
            top_bit = (register_val >> (bit_len - 1)) & 1
            register_val = ((register_val << 1) | extracted_bit) & 0xFFFFFFFF
            if top_bit:
                register_val ^= poly

    # --- Phase 2: flush bit_len zero bits ---
    for _ in range(bit_len):
        top_bit = (register_val >> (bit_len - 1)) & 1
        register_val = (register_val << 1) & 0xFFFFFFFF
        if top_bit:
            register_val ^= poly

    return register_val & boundary


def verify_crc(data: bytes | bytearray, received_crc: int,
               poly: int = 0x04C11DB7, bit_len: int = 32) -> bool:
    """Return True if the recomputed CRC matches *received_crc*."""
    return compute_crc(data, poly, bit_len) == received_crc


# ---------------------------------------------------------------------------
# Convenience: pack/unpack FCS as 4-byte big-endian (for frame trailer)
# ---------------------------------------------------------------------------

def fcs_to_bytes(crc32_value: int) -> bytes:
    """Pack a 32-bit CRC into 4 big-endian bytes."""
    return crc32_value.to_bytes(4, byteorder='big')


def bytes_to_fcs(raw: bytes | bytearray) -> int:
    """Unpack 4 big-endian bytes back to a 32-bit integer."""
    return int.from_bytes(raw[:4], byteorder='big')


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sample = b"Hello, Network!"

    cs = compute_checksum(sample)
    print(f"[Checksum] data={sample!r}")
    print(f"           checksum = 0x{cs:04X}")
    print(f"           verify   = {verify_checksum(sample, cs)}\n")

    crc32 = compute_crc(sample)
    print(f"[CRC-32]   data={sample!r}")
    print(f"           crc32  = 0x{crc32:08X}")
    print(f"           verify = {verify_crc(sample, crc32)}")
    print(f"           packed = {fcs_to_bytes(crc32).hex(':')}")
