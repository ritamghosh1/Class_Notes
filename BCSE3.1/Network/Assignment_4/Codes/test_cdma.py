"""
test_cdma.py
============
Comprehensive Automated Test Suite for CDMA with Walsh Codes.

Includes rigorous unit and integration tests verifying:
  - Hadamard matrix properties, symmetry, and recursive generation
  - Mathematical orthogonality: <W_i, W_j> = N * delta_{i,j}
  - Bipolar NRZ mapping and chip spreading
  - Linear superposition on shared channel
  - Despreading, matched filtering, and thresholding
  - Multi-station concurrent transmission of arbitrary bits and ASCII strings
  - TRUE MULTI-PROCESS EXECUTION: k independent OS processes, distinct PIDs, and IPC pipes
  - Silent/idle station isolation and non-interference
  - Noise tolerance under AWGN conditions
  - Dimension edge cases (odd stations, single station, large n)

Usage:
    python3 Codes/test_cdma.py
"""

from __future__ import annotations
import os
import unittest
import numpy as np

try:
    from walsh import WalshCodeGenerator
    from channel import Channel
    from station import Station, Sender, Receiver
    from simulation import CDMASimulation, MultiProcessCDMASimulation
except ImportError:
    from Codes.walsh import WalshCodeGenerator
    from Codes.channel import Channel
    from Codes.station import Station, Sender, Receiver
    from Codes.simulation import CDMASimulation, MultiProcessCDMASimulation


class TestWalshCodeGenerator(unittest.TestCase):
    """Unit tests for Walsh-Hadamard code generation and properties."""

    def test_next_power_of_two(self):
        self.assertEqual(WalshCodeGenerator.next_power_of_two(1), 2)
        self.assertEqual(WalshCodeGenerator.next_power_of_two(2), 2)
        self.assertEqual(WalshCodeGenerator.next_power_of_two(3), 4)
        self.assertEqual(WalshCodeGenerator.next_power_of_two(4), 4)
        self.assertEqual(WalshCodeGenerator.next_power_of_two(5), 8)
        self.assertEqual(WalshCodeGenerator.next_power_of_two(16), 16)
        self.assertEqual(WalshCodeGenerator.next_power_of_two(17), 32)

    def test_hadamard_dimensions_and_entries(self):
        for n in [2, 4, 8, 16, 32]:
            h = WalshCodeGenerator.generate_hadamard_matrix(n)
            self.assertEqual(h.shape, (n, n))
            unique_vals = set(np.unique(h))
            self.assertTrue(unique_vals.issubset({1, -1}))

    def test_hadamard_symmetry(self):
        for n in [2, 4, 8, 16]:
            h = WalshCodeGenerator.generate_hadamard_matrix(n)
            np.testing.assert_array_equal(h, h.T)

    def test_hadamard_orthogonality(self):
        for n in [2, 4, 8, 16, 32]:
            h = WalshCodeGenerator.generate_hadamard_matrix(n)
            is_ortho, g = WalshCodeGenerator.verify_orthogonality(h)
            self.assertTrue(is_ortho)
            np.testing.assert_array_equal(g, n * np.eye(n, dtype=int))

    def test_invalid_dimensions(self):
        with self.assertRaises(ValueError):
            WalshCodeGenerator.generate_hadamard_matrix(3)
        with self.assertRaises(ValueError):
            WalshCodeGenerator.generate_hadamard_matrix(0)
        with self.assertRaises(ValueError):
            WalshCodeGenerator.generate_hadamard_matrix(10)


class TestChannel(unittest.TestCase):
    """Unit tests for shared CDMA channel simulation."""

    def test_linear_superposition(self):
        chan = Channel(code_length=4)
        sig1 = np.array([1, 1, 1, 1])
        sig2 = np.array([1, -1, 1, -1])
        comp = chan.transmit_slot({0: sig1, 1: sig2})
        expected = np.array([2.0, 0.0, 2.0, 0.0])
        np.testing.assert_array_equal(comp, expected)

    def test_idle_channel(self):
        chan = Channel(code_length=4)
        comp = chan.transmit_slot({})
        np.testing.assert_array_equal(comp, np.zeros(4))

    def test_channel_telemetry(self):
        chan = Channel(code_length=4)
        chan.transmit_slot({0: np.array([1, 1, 1, 1])})
        chan.transmit_slot({0: np.array([1, 1, 1, 1])})
        self.assertEqual(chan.total_slots, 2)
        self.assertEqual(chan.total_chips_transmitted, 8)
        self.assertEqual(len(chan.signal_history), 2)


class TestStationComponents(unittest.TestCase):
    """Unit tests for Sender and Receiver implementations."""

    def test_sender_bipolar_encoding(self):
        code = np.array([1, -1, 1, -1])
        sender = Sender(station_id=0, walsh_code=code)
        sender.load_bits([1, 0, None])

        c1 = sender.get_next_chips()
        np.testing.assert_array_equal(c1, np.array([1, -1, 1, -1]))

        c2 = sender.get_next_chips()
        np.testing.assert_array_equal(c2, np.array([-1, 1, -1, 1]))

        c3 = sender.get_next_chips()
        np.testing.assert_array_equal(c3, np.array([0, 0, 0, 0]))

    def test_receiver_matched_filtering(self):
        code = np.array([1, 1, 1, 1])
        receiver = Receiver(station_id=0, walsh_code=code)

        b1, norm1 = receiver.decode_chips(np.array([1, 1, 1, 1]))
        self.assertEqual(b1, 1)
        self.assertAlmostEqual(norm1, 1.0)

        b0, norm0 = receiver.decode_chips(np.array([-1, -1, -1, -1]))
        self.assertEqual(b0, 0)
        self.assertAlmostEqual(norm0, -1.0)

        bn, norm_n = receiver.decode_chips(np.array([0, 0, 0, 0]))
        self.assertIsNone(bn)
        self.assertAlmostEqual(norm_n, 0.0)

    def test_text_serialization_and_reconstruction(self):
        code = np.array([1, 1, 1, 1])
        sender = Sender(station_id=0, walsh_code=code)
        receiver = Receiver(station_id=0, walsh_code=code)

        msg = "TEST"
        sender.load_text(msg)
        self.assertEqual(len(sender.bit_queue), 32)

        while sender.has_pending_data():
            chips = sender.get_next_chips()
            receiver.decode_chips(chips)

        self.assertEqual(receiver.get_message(), msg)


class TestCDMASimulation(unittest.TestCase):
    """Integration tests for CDMA communication."""

    def test_two_station_concurrent_bits(self):
        sim = CDMASimulation(num_stations=2, payloads=[[1, 0, 1], [0, 1, 1]])
        rep = sim.run_all()
        self.assertTrue(rep["all_perfect"])
        self.assertEqual(rep["total_errors"], 0)
        self.assertEqual(rep["overall_ber"], 0.0)

    def test_four_station_text_transmission(self):
        messages = ["NET4", "CDMA", "SYNC", "WALS"]
        sim = CDMASimulation(num_stations=4, payloads=messages)
        rep = sim.run_all()
        self.assertTrue(rep["all_perfect"])
        self.assertEqual(rep["overall_ber"], 0.0)
        for i, s_rep in enumerate(rep["station_reports"]):
            self.assertEqual(s_rep["reconstructed_message"], messages[i])
            self.assertTrue(s_rep["is_perfect"])

    def test_eight_station_concurrent_data(self):
        sim = CDMASimulation(num_stations=8)
        sim.load_default_text_payloads()
        rep = sim.run_all()
        self.assertTrue(rep["all_perfect"])
        self.assertEqual(rep["total_errors"], 0)

    def test_silent_stations_isolation(self):
        payloads = [
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [None, None, None, None],
            [1, 1, 0, 0]
        ]
        sim = CDMASimulation(num_stations=4, payloads=payloads)
        rep = sim.run_all()
        self.assertTrue(rep["all_perfect"])
        self.assertEqual(sim.stations[2].receiver.received_bits, [None, None, None, None])

    def test_odd_station_counts(self):
        sim = CDMASimulation(num_stations=3, payloads=["A", "B", "C"])
        self.assertEqual(sim.code_length, 4)
        rep = sim.run_all()
        self.assertTrue(rep["all_perfect"])

    def test_high_snr_awgn_accuracy(self):
        sim = CDMASimulation(num_stations=4, snr_db=25.0, payloads=["DATA", "TEST", "INFO", "FAST"])
        rep = sim.run_all()
        self.assertTrue(rep["all_perfect"])
        self.assertEqual(rep["total_errors"], 0)


class TestMultiProcessCDMA(unittest.TestCase):
    """
    Integration tests verifying TRUE MULTI-PROCESS execution:
    k stations run in k independent OS processes with distinct PIDs.
    """

    def test_multiprocess_pid_isolation(self):
        k = 4
        sim = MultiProcessCDMASimulation(num_stations=k, payloads=["A", "B", "C", "D"])
        pids = list(sim.station_pids.values())
        main_pid = os.getpid()

        # All k station processes must have unique PIDs
        self.assertEqual(len(set(pids)), k, "All k stations must have distinct OS PIDs")
        # All k child PIDs must be distinct from the orchestrator PID
        for p in pids:
            self.assertNotEqual(p, main_pid, "Child process PID must differ from main PID")

        rep = sim.run_all()
        self.assertTrue(rep["all_perfect"])
        self.assertEqual(rep["total_errors"], 0)

    def test_multiprocess_text_reconstruction(self):
        messages = ["NET4", "CDMA", "SYNC", "WALS"]
        sim = MultiProcessCDMASimulation(num_stations=4, payloads=messages)
        rep = sim.run_all()
        self.assertTrue(rep["all_perfect"])
        self.assertEqual(rep["overall_ber"], 0.0)
        for i, s_rep in enumerate(rep["station_reports"]):
            self.assertEqual(s_rep["reconstructed_message"], messages[i])
            self.assertTrue(s_rep["is_perfect"])

    def test_multiprocess_eight_stations(self):
        messages = ["N1", "C2", "S3", "W4", "P5", "M6", "R7", "C8"]
        sim = MultiProcessCDMASimulation(num_stations=8, payloads=messages)
        self.assertEqual(len(sim.station_pids), 8)
        self.assertEqual(len(set(sim.station_pids.values())), 8)
        rep = sim.run_all()
        self.assertTrue(rep["all_perfect"])
        self.assertEqual(rep["total_errors"], 0)


def run_tests():
    """Runs all test cases and prints clean summary."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    run_tests()
