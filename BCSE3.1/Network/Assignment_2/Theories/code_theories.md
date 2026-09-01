# Data Link Layer Simulation: Code Theories & Organization

This document provides a detailed breakdown of the theoretical concepts behind each Python module in the Assignment 2 Data Link Layer Simulation project.

---

## 1. Code Organization & Architecture

The project is structured in a highly modular way, separating the concerns of the Data Link Layer into distinct components. This mimics how a real networking stack is implemented.

*   **Top Level (Protocols):** `sender.py` and `receiver.py` act as the end-hosts. They implement the state machines for Stop-and-Wait (SAW), Go-Back-N (GBN), and Selective Repeat (SR).
*   **Data Link Sub-layers:**
    *   *Framing & Encapsulation:* `frame.py`
    *   *Error Control:* `error_detection.py` and `timer.py`
*   **Physical Layer Simulation:** `channel.py` and `error_injection.py` act as the unreliable medium (the "wire") connecting the sender and receiver.
*   **UI/Visualization:** `dashboard.py` provides real-time monitoring of the protocol states.

### Data Flow
1. `sender.py` reads data and uses `frame.py` to encapsulate it into frames (attaching CRC).
2. It sends frames via `channel.py`, starting timers using `timer.py`.
3. `channel.py` simulates delay, loss, and uses `error_injection.py` to occasionally corrupt bits, then delivers the frame over a TCP socket.
4. `receiver.py` receives the frame, uses `frame.py` to verify the CRC. If valid, it processes the sequence number and sends an ACK back through the channel.

---

## 2. Detailed Theories for Each Module

### `sender.py` & `receiver.py` (The ARQ Protocols)
**Theory:** These modules implement Automatic Repeat reQuest (ARQ) protocols to achieve reliable data transfer over an unreliable channel.
*   **Stop-and-Wait (SAW):** The simplest protocol. The sender transmits one frame and waits for an ACK before sending the next. It has a window size of 1. Very inefficient for links with high propagation delay (high RTT).
*   **Go-Back-N (GBN):** Allows the sender to transmit multiple frames (up to a window size N) before needing an ACK. The receiver only accepts frames in strict sequence. If a frame is lost, the receiver discards all subsequent frames, and the sender must retransmit the *entire* window of unacknowledged frames.
*   **Selective Repeat (SR):** The most efficient protocol. Both sender and receiver maintain a window. The receiver buffers out-of-order frames and sends individual ACKs (or NAKs). If a frame is lost, the sender only retransmits that specific frame, saving bandwidth.

### `frame.py` (Framing)
**Theory:** At the Data Link layer, raw bit streams are organized into discrete units called **frames**. 
*   This module encapsulates the payload by adding a header (Source MAC, Destination MAC, Sequence Number) and a trailer (Frame Check Sequence / CRC). 
*   This structure allows the receiver to determine where a packet starts/ends and validates its integrity.

### `error_detection.py` (CRC-32 & Checksum)
**Theory:** Noise in the physical medium can flip bits. 
*   **CRC-32 (Cyclic Redundancy Check):** A robust error-detecting code based on polynomial division. The sender treats the data as a large binary polynomial, divides it by a standard generator polynomial (like IEEE 802.3), and appends the remainder (FCS). The receiver does the same division; if the remainder is 0, the frame is assumed error-free.
*   **Internet Checksum:** Used traditionally in IP/TCP. It sums the 16-bit words of the data and takes the 1's complement. Less robust than CRC but computationally cheaper.

### `error_injection.py` & `channel.py` (Unreliable Channel Simulation)
**Theory:** To test ARQ protocols, we must simulate real-world network imperfections.
*   `channel.py` intercepts packets before they hit the network socket. It applies a uniform probability model to either drop the packet entirely (`p-loss`) or delay it.
*   `error_injection.py` flips specific bits in the byte array to simulate noise (e.g., thermal noise causing a single bit flip, or impulse noise causing a burst error).

### `timer.py` (RTT Estimation & RTO)
**Theory:** To detect lost packets, ARQ protocols use timers. 
*   If a timer is fixed and too short, it causes unnecessary retransmissions. If too long, the protocol becomes slow to recover.
*   This module implements **RFC 6298**. It measures the Round Trip Time (RTT) of ACKs and uses an Exponentially Weighted Moving Average (EWMA) to calculate a Smoothed RTT (SRTT) and RTT Variance (RTTVAR). 
*   The Retransmission Timeout (RTO) is dynamically calculated as: RTO = SRTT + max(G, 4 * RTTVAR).

### `dashboard.py` (Live UI)
**Theory:** This is a visualization tool built using the `rich` library. It reads the internal state variables of the sender and receiver (like `base`, `next_seq_num`, and `rtt_samples`) in a thread-safe manner (using Mutex locks) and renders a live UI at a high refresh rate.

---

## 3. Understanding the Dashboard Output

When you run the programs with the `--dashboard` flag, a live terminal UI replaces the standard scrolling text output. Here is how to interpret it for your presentation:

### Sliding Window (Top Left)
*   Shows a visual representation of the buffer.
*   **Base:** The sequence number of the oldest unacknowledged frame.
*   **Next:** The sequence number of the next frame to be sent.
*   **Symbols:**
    *   `[✓]` **Green:** Frame successfully ACKed.
    *   `[▶]` **Cyan:** Frame transmitted, currently in flight or waiting for ACK.
    *   `[⚡]` **Yellow:** Timeout occurred, frame is pending retransmission.
    *   `[✗]` **Red:** NAK received (in SR protocol).

### Metrics (Top Right)
*   **Original vs Retransmits:** Shows how many unique frames were sent vs how many had to be resent due to errors/loss.
*   **Efficiency:** Calculates `(Original / Total Frames Sent) * 100`. In a perfect channel, this is 100%. If `p-error` is high, this drops significantly. GBN will show a much sharper drop in efficiency compared to SR at the same error rate.
*   **Throughput:** Bytes successfully transferred per second.

### RTT / RTO Sparklines (Bottom Left)
*   **RTT (Cyan):** A live graph of the measured Round Trip Time for recent frames.
*   **RTO (Red):** A live graph of the dynamic timeout value. You can see the RTO adjust dynamically if the channel delay spikes.

### Event Log (Bottom Right)
*   A scrolling list of recent events (e.g., "Sent frame 4", "TIMEOUT idx=2", "ACK 3"). This is useful for debugging exactly when a frame was dropped.
