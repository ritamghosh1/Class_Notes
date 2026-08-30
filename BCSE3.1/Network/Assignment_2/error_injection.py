"""
error_injection.py
==================
Python port of ErrorInjection.cpp (Assignment 1).

Provides six error-injection strategies that mutate a bytearray in-place,
exactly mirroring the C++ methods in ErrorInjection.cpp:

  1. introduce_random_bit_flip      — flip one random bit
  2. introduce_double_bit_flip      — flip two non-adjacent random bits
  3. introduce_odd_anomalies        — flip an odd number (3/5/7) of random bits
  4. introduce_burst_noise          — flip a contiguous run of bits
  5. introduce_checksum_collision   — create a data change invisible to checksum
  6. introduce_word_swap            — swap two 16-bit words in the payload area
  7. introduce_crc8_collision       — XOR the CRC-8 generator pattern into data

All functions accept and return a bytearray.  If you pass bytes, they are
converted internally; the mutated bytearray is always returned so callers
can either use the return value or rely on in-place mutation.

Typical usage:
    from error_injection import introduce_random_bit_flip
    corrupted = introduce_random_bit_flip(bytearray(frame_bytes))
"""

import random
from typing import Union

# Type alias accepted by all functions
_Buf = Union[bytes, bytearray]


def _ensure_mutable(data: _Buf) -> bytearray:
    """Return a bytearray, copying if necessary."""
    return data if isinstance(data, bytearray) else bytearray(data)


# ---------------------------------------------------------------------------
# 1. Random single-bit flip  (introduceRandomBitFlip)
# ---------------------------------------------------------------------------

def introduce_random_bit_flip(packet: _Buf) -> bytearray:
    """
    Flip one randomly chosen bit in *packet*.

    Mirrors C++:
        int target = dist(engine);
        packet[target / 8] ^= (1 << (target % 8));
    """
    buf = _ensure_mutable(packet)
    if not buf:
        return buf
    num_bits = len(buf) * 8
    if num_bits < 3:
        return buf
    target = random.randrange(num_bits)
    buf[target // 8] ^= (1 << (target % 8))
    return buf


# ---------------------------------------------------------------------------
# 2. Double bit flip  (introduceDoubleBitFlip)
# ---------------------------------------------------------------------------

def introduce_double_bit_flip(packet: _Buf) -> bytearray:
    """
    Flip two randomly chosen bits that are *not adjacent* (|i - j| > 1).

    Mirrors C++:
        while (!found) {
            secondTarget = dist(engine);
            if (std::abs(firstTarget - secondTarget) > 1) found = true;
        }
    """
    buf = _ensure_mutable(packet)
    if not buf:
        return buf
    num_bits = len(buf) * 8
    if num_bits < 3:
        return buf

    first = random.randrange(num_bits)
    second = first
    while abs(first - second) <= 1:
        second = random.randrange(num_bits)

    buf[first  // 8] ^= (1 << (first  % 8))
    buf[second // 8] ^= (1 << (second % 8))
    return buf


# ---------------------------------------------------------------------------
# 3. Odd number of bit anomalies  (introduceOddAnomalies)
# ---------------------------------------------------------------------------

def introduce_odd_anomalies(packet: _Buf) -> bytearray:
    """
    Flip an odd number of randomly chosen bits (3, 5, or 7).

    Mirrors C++:
        int anomalyCount = 3 + (distOdd(engine) * 2);   // 3, 5, or 7
        // collect unique bit positions and flip them
    """
    buf = _ensure_mutable(packet)
    if not buf:
        return buf
    num_bits = len(buf) * 8

    # Choose odd anomaly count: 3, 5, or 7 (matches C++ distOdd(engine) in [0,2])
    anomaly_count = 3 + random.randint(0, 2) * 2  # 3, 5, or 7

    if anomaly_count > num_bits:
        # Clamp to largest odd number ≤ num_bits
        anomaly_count = num_bits if num_bits % 2 != 0 else num_bits - 1
        if anomaly_count <= 0:
            return buf

    # Pick unique bit positions (using a set, just like the C++ unordered_set)
    mutated_bits = random.sample(range(num_bits), anomaly_count)
    for target in mutated_bits:
        buf[target // 8] ^= (1 << (target % 8))
    return buf


# ---------------------------------------------------------------------------
# 4. Burst noise  (introduceBurstNoise)
# ---------------------------------------------------------------------------

def introduce_burst_noise(packet: _Buf, noise_length: int = 8) -> bytearray:
    """
    Flip a contiguous run of *noise_length* bits starting at a random position.

    Mirrors C++:
        int startPos = startDist(engine);
        for k in range(noiseLength): packet[(startPos+k)/8] ^= ...
    """
    buf = _ensure_mutable(packet)
    if not buf or noise_length <= 1:
        return buf
    num_bits = len(buf) * 8
    if noise_length > num_bits:
        noise_length = num_bits

    start_pos = random.randint(0, num_bits - noise_length)
    for k in range(noise_length):
        target = start_pos + k
        buf[target // 8] ^= (1 << (target % 8))
    return buf


# ---------------------------------------------------------------------------
# 5. Checksum collision  (introduceChecksumCollision)
# ---------------------------------------------------------------------------

def introduce_checksum_collision(packet: _Buf) -> bytearray:
    """
    Modify two 16-bit words in the payload so that the Internet Checksum is
    unchanged — making the corruption *invisible* to checksum verification.

    Strategy (mirrors C++):
      Find two words at positions w1 and w2 where the same bit position has
      opposite values.  Flip that bit in both words — the checksum sum is
      unaffected because the two changes cancel each other.

    Falls back to introduce_random_bit_flip if no suitable pair is found
    within 200 attempts.

    The last 2 bytes are treated as the checksum field and are excluded from
    the search window (mirrors C++ `dataSize = packet.size() - 2`).
    """
    buf = _ensure_mutable(packet)
    if len(buf) <= 2:
        return buf

    data_size = len(buf) - 2          # exclude trailing checksum field
    if data_size < 4:
        return buf

    num_words = data_size // 2        # number of 16-bit words available

    def read_word(word_index: int) -> int:
        base = word_index * 2
        return (buf[base] << 8) | buf[base + 1]

    def flip_word_bit(word_index: int, bit_pos: int) -> None:
        # Mirrors C++ flipWordBit lambda (big-endian word layout)
        base = word_index * 2
        if bit_pos >= 8:
            buf[base]     ^= (1 << (bit_pos - 8))
        else:
            buf[base + 1] ^= (1 << bit_pos)

    for _ in range(200):
        w1 = random.randrange(num_words)
        w2 = random.randrange(num_words)
        if w1 == w2:
            continue

        bit_pos = random.randrange(16)
        word_a  = read_word(w1)
        word_b  = read_word(w2)
        bit_a   = (word_a >> bit_pos) & 1
        bit_b   = (word_b >> bit_pos) & 1

        if bit_a != bit_b:
            flip_word_bit(w1, bit_pos)
            flip_word_bit(w2, bit_pos)
            return buf

    # Fallback: could not find a collision pair — just flip one random bit
    return introduce_random_bit_flip(buf)


# ---------------------------------------------------------------------------
# 6. Word swap  (introduceWordSwap)
# ---------------------------------------------------------------------------

# Header size assumed in C++ was 16 bytes (their NetworkFrameHeader struct).
# Our Assignment-2 frame header is 15 bytes — adjust if needed.
_HEADER_SIZE = 15   # 6 (src MAC) + 6 (dst MAC) + 2 (length) + 1 (seq_no)
_TRAILER_SIZE = 4   # FCS

def introduce_word_swap(packet: _Buf, header_size: int = _HEADER_SIZE) -> bytearray:
    """
    Swap two randomly chosen 16-bit words in the *payload* area (excludes
    the header and the FCS trailer), so the frame structure is not destroyed
    but the data is still corrupted.

    Mirrors C++ (adjusted header_size from 16 → 15 to match our frame):
        size_t dataSize = packet.size() - headerSize - 4;
    """
    buf = _ensure_mutable(packet)
    if len(buf) < header_size + _TRAILER_SIZE + 4:
        return buf

    data_size = len(buf) - header_size - _TRAILER_SIZE
    if data_size < 4:
        return buf

    num_words = data_size // 2
    w1 = random.randrange(num_words)
    w2 = random.randrange(num_words)
    while w1 == w2:
        w2 = random.randrange(num_words)

    idx1 = header_size + w1 * 2
    idx2 = header_size + w2 * 2

    buf[idx1], buf[idx2]         = buf[idx2], buf[idx1]
    buf[idx1 + 1], buf[idx2 + 1] = buf[idx2 + 1], buf[idx1 + 1]
    return buf


# ---------------------------------------------------------------------------
# 7. CRC-8 collision  (introduceCRC8Collision)
# ---------------------------------------------------------------------------

def introduce_crc8_collision(packet: _Buf, header_size: int = _HEADER_SIZE) -> bytearray:
    """
    XOR the CRC-8 generator bitmask (0xEA, 0x80) into two consecutive bytes
    of the payload, creating a change that is invisible to CRC-8 checking.

    From C++ comments:
        // CRC-8 polynomial is 0x1D5 (1 1101 0101).
        // To cause a collision, the error polynomial must be a multiple of
        // the generator polynomial.  XOR pattern: 0xEA 0x80.

    Targets a random position within the payload (skips header, stays 2 bytes
    away from the end to avoid touching the FCS).
    """
    buf = _ensure_mutable(packet)
    # Need at least header + 2 payload bytes + FCS
    if len(buf) < header_size + 2 + _TRAILER_SIZE:
        return buf

    # Valid range: [header_size, len - FCS - 2]  (need room for 2-byte XOR)
    lo = header_size
    hi = len(buf) - _TRAILER_SIZE - 2   # inclusive upper bound
    if lo > hi:
        return buf

    pos = random.randint(lo, hi)
    buf[pos]     ^= 0xEA
    buf[pos + 1] ^= 0x80
    return buf


# ---------------------------------------------------------------------------
# Convenience: probabilistic injection (for Channel simulation)
# ---------------------------------------------------------------------------

def inject_error(packet: _Buf, probability: float = 0.1,
                 mode: str = "random_bit") -> bytearray:
    """
    Probabilistic wrapper: corrupt *packet* with the given *probability*.

    Parameters
    ----------
    packet      : bytes or bytearray
    probability : float in [0.0, 1.0] — chance that an error is injected
    mode        : one of
                    "random_bit"         -> introduce_random_bit_flip
                    "double_bit"         -> introduce_double_bit_flip
                    "odd_anomalies"      -> introduce_odd_anomalies
                    "burst"              -> introduce_burst_noise
                    "checksum_collision" -> introduce_checksum_collision
                    "word_swap"          -> introduce_word_swap
                    "crc8_collision"     -> introduce_crc8_collision

    Returns
    -------
    bytearray — possibly corrupted copy of *packet*
    """
    buf = _ensure_mutable(packet)
    if random.random() >= probability:
        return buf      # no error this time

    dispatch = {
        "random_bit":         introduce_random_bit_flip,
        "double_bit":         introduce_double_bit_flip,
        "odd_anomalies":      introduce_odd_anomalies,
        "burst":              introduce_burst_noise,
        "checksum_collision": introduce_checksum_collision,
        "word_swap":          introduce_word_swap,
        "crc8_collision":     introduce_crc8_collision,
    }
    fn = dispatch.get(mode, introduce_random_bit_flip)
    return fn(buf)


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    original = bytearray(b"Hello, DataLink Layer! " * 4)   # 88 bytes
    print(f"Original  : {original[:20].hex(' ')} ...")

    flipped = introduce_random_bit_flip(bytearray(original))
    diffs = sum(a != b for a, b in zip(original, flipped))
    print(f"RandomBit : {flipped[:20].hex(' ')} ... (bytes changed: {diffs})")

    burst = introduce_burst_noise(bytearray(original), noise_length=16)
    diffs = sum(a != b for a, b in zip(original, burst))
    print(f"Burst(16) : {burst[:20].hex(' ')} ... (bytes changed: {diffs})")

    prob_result = inject_error(bytearray(original), probability=1.0, mode="odd_anomalies")
    diffs = sum(a != b for a, b in zip(original, prob_result))
    print(f"OddAnom   : {prob_result[:20].hex(' ')} ... (bytes changed: {diffs})")
