"""
walsh.py
========
Walsh-Hadamard Code Generator and Orthogonality Engine.

Implements recursive Sylvester Hadamard matrix construction,
Walsh code generation, orthogonal property verification, and chip sequence mapping.

Mathematics:
    H_1 = [1]
    H_{2N} = [ [H_N,  H_N],
               [H_N, -H_N] ]

Orthogonality condition:
    W_i · W_j = sum_{k=0}^{N-1} W_i[k] * W_j[k] = N if i == j else 0
"""

from __future__ import annotations
import math
import numpy as np


class WalshCodeGenerator:
    """
    Generates and manages Walsh-Hadamard codes for CDMA multiplexing.
    """

    @staticmethod
    def next_power_of_two(n: int) -> int:
        """
        Calculates the smallest power of 2 greater than or equal to n.
        CDMA Walsh matrices require dimensions of power-of-2 (N >= 2).
        """
        if n <= 1:
            return 2
        return 1 << (n - 1).bit_length()

    @classmethod
    def generate_hadamard_matrix(cls, dimension: int) -> np.ndarray:
        """
        Generates a Hadamard matrix of given dimension using Sylvester's recursive construction.

        Args:
            dimension: Dimension N (must be a power of 2).

        Returns:
            np.ndarray: N x N orthogonal matrix with entries in {+1, -1}.

        Raises:
            ValueError: If dimension is not a positive power of 2.
        """
        if dimension <= 0 or (dimension & (dimension - 1)) != 0:
            raise ValueError(f"Hadamard dimension must be a power of 2, got {dimension}")

        if dimension == 1:
            return np.array([[1]], dtype=np.int32)

        # Base 2x2 Hadamard matrix
        h2 = np.array([[1, 1], [1, -1]], dtype=np.int32)
        if dimension == 2:
            return h2

        # Recursive Sylvester expansion
        k = int(math.log2(dimension))
        h = h2
        for _ in range(1, k):
            h = np.block([[h, h], [h, -h]])

        return h.astype(np.int32)

    @classmethod
    def get_walsh_set(cls, num_stations: int) -> tuple[np.ndarray, int]:
        """
        Generates a Walsh set sufficient to support num_stations unique codes.

        Args:
            num_stations: Number of transmitting stations.

        Returns:
            tuple[np.ndarray, int]: (Hadamard matrix H_N, code length N).
        """
        code_length = cls.next_power_of_two(num_stations)
        hadamard_matrix = cls.generate_hadamard_matrix(code_length)
        return hadamard_matrix, code_length

    @classmethod
    def get_code_for_station(cls, station_id: int, num_stations: int) -> np.ndarray:
        """
        Retrieves the unique Walsh codeword assigned to a given station ID.

        Args:
            station_id: Zero-indexed station identifier (0 <= station_id < num_stations).
            num_stations: Total number of stations in the network.

        Returns:
            np.ndarray: 1D array of length N containing chip values (+1 or -1).
        """
        if station_id < 0 or station_id >= num_stations:
            raise IndexError(f"Station ID {station_id} out of bounds for {num_stations} stations")

        h_matrix, _ = cls.get_walsh_set(num_stations)
        return h_matrix[station_id].copy()

    @staticmethod
    def inner_product(code_a: np.ndarray, code_b: np.ndarray) -> int:
        """
        Computes the discrete inner (dot) product between two Walsh codewords:
            <A, B> = sum_{k=0}^{N-1} A[k] * B[k]
        """
        return int(np.dot(code_a, code_b))

    @classmethod
    def verify_orthogonality(cls, hadamard_matrix: np.ndarray) -> tuple[bool, np.ndarray]:
        """
        Verifies that all rows in the Hadamard matrix are mutually orthogonal.
        Computes the Gramian matrix: G = H · H^T.
        For perfect orthogonality: G = N · I_N.

        Returns:
            tuple[bool, np.ndarray]: (is_orthogonal, gramian_matrix).
        """
        n = hadamard_matrix.shape[0]
        gramian = np.dot(hadamard_matrix, hadamard_matrix.T)
        expected = n * np.eye(n, dtype=np.int32)
        is_orthogonal = bool(np.array_equal(gramian, expected))
        return is_orthogonal, gramian

    @staticmethod
    def format_code(code: np.ndarray) -> str:
        """
        Returns a clean string representation of a codeword (e.g., '[+1, -1, +1, -1]').
        """
        elements = [f"+1" if x > 0 else f"-1" for x in code]
        return f"[{', '.join(elements)}]"


if __name__ == "__main__":
    print("=== Self-Test: Walsh Code Generator ===")
    for test_n in [2, 4, 8]:
        H, N = WalshCodeGenerator.get_walsh_set(test_n)
        is_ortho, G = WalshCodeGenerator.verify_orthogonality(H)
        print(f"\nStations: {test_n} -> Code Length N = {N}")
        print(f"Hadamard Matrix H_{N}:\n{H}")
        print(f"Orthogonality Verified: {is_ortho}")
        for i in range(test_n):
            print(f"  Station {i}: {WalshCodeGenerator.format_code(H[i])}")
