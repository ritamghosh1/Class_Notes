# Operating Systems Laboratory - Assignment II

## Problem 1: Inter-Process Communication (IPC) Synchronization using Pipes

### Problem Statement Breakdown
We are given two processes, **Process X** and **Process Y**, interacting with two pieces of data, **x** and **y**.
- **Process X's Role:** It needs to generate/write data `x` and consume/read data `y`.
- **Process Y's Role:** It needs to generate/write data `y` and consume/read data `x`.

### The Synchronization Constraint
The core challenge is ensuring things happen in the correct order:
1. **Y cannot read `x` until X has written it.** (Y must wait for X).
2. **X cannot read `y` until Y has written it.** (X must wait for Y).

If we don't enforce this, Process Y might try to read `x` before it actually exists (resulting in garbage or empty data), and similarly for Process X reading `y`.

### The Concept of Pipes
A **pipe** is a mechanism for Inter-Process Communication (IPC). You can think of it as a one-way data hose connecting two processes. 
- It has a **write end** (where one process pumps data in) and a **read end** (where another process reads data out).
- **Crucial Property (Blocking):** If a process tries to read from an empty pipe, the operating system puts that process to sleep (blocks it) until another process writes data into the pipe. This blocking behavior is exactly what we use to solve our synchronization problem without needing complex locking mechanisms.

### The Solution Design
Since pipes are one-way (unidirectional), and we need data to flow in both directions (X to Y, and Y to X), we must use **two separate pipes**:

*   **Pipe 1 (Data `x` flow):** 
    *   **Write End:** Connected to Process X.
    *   **Read End:** Connected to Process Y.
*   **Pipe 2 (Data `y` flow):** 
    *   **Write End:** Connected to Process Y.
    *   **Read End:** Connected to Process X.

### Step-by-Step Execution Flow
Here is how the processes will execute to guarantee the constraints are met:

**Process X:**
1.  **Write `x` into Pipe 1:** Process X completes its writing task. Data `x` is now sitting in Pipe 1.
2.  **Read `y` from Pipe 2:** Process X attempts to read from Pipe 2. 
    *   *Scenario A:* If Process Y has already written `y`, Process X reads it immediately and continues.
    *   *Scenario B:* If Process Y has NOT written `y` yet, Pipe 2 is empty. Process X will automatically **block** (wait) right here until Y writes to it. This satisfies the constraint: "X must not read y until Y has written to it."

**Process Y:**
1.  **Write `y` into Pipe 2:** Process Y completes its writing task. Data `y` is now sitting in Pipe 2.
2.  **Read `x` from Pipe 1:** Process Y attempts to read from Pipe 1.
    *   *Scenario A:* If Process X has already written `x`, Process Y reads it immediately and continues.
    *   *Scenario B:* If Process X has NOT written `x` yet, Pipe 1 is empty. Process Y will automatically **block** (wait) right here until X writes to it. This satisfies the constraint: "Y must not read x until X has written to it."

By structuring the order of operations as `Write -> Read` for both processes across two distinct pipes, we inherently create a synchronized, deadlock-free system utilizing the OS's built-in pipe blocking mechanism.

## Core Concepts: Processes and Forking

### What is `pid_t`?
`pid_t` stands for **Process ID Type**. It is a special data type defined in the `<sys/types.h>` header file.

Under the hood, it is usually just a signed integer (like a regular `int`), but you should always use `pid_t` when dealing with process IDs because it guarantees that your code will be portable across different operating systems and architectures. It clearly tells anyone reading the code (and the compiler) that "this variable is meant to hold a Process ID".

### The Purpose of `pid` and `fork()`
When you write `pid_t pid = fork();`, you are using the `fork()` function.

When you call `fork()`, the operating system takes your currently running program and clones it, creating an almost identical "child" process. After `fork()` executes, you suddenly have **two** processes running the exact same code from that line onwards.

The variable `pid` captures the return value of the `fork()` function, which is how the two processes know which one they are so they can do different jobs (like Process X vs. Process Y).

`fork()` behaves uniquely by returning *different values* depending on which process is looking at it:
1.  **In the Parent Process:** `fork()` returns the actual positive Process ID (PID) of the newly created child.
2.  **In the Child Process:** `fork()` returns exactly `0`.
3.  **(Error case):** If the OS failed to create a new process, `fork()` returns `-1`.

By storing this return value in `pid`, you can use an `if/else` statement right after it to split the logic:

```c
pid_t pid = fork();

if (pid == -1) {
    // Fork failed
    perror("Fork failed");
    return 1;
} else if (pid == 0) {
    // This block ONLY runs in the CHILD process (e.g., Process Y)
} else {
    // This block ONLY runs in the PARENT process (e.g., Process X)
}
```

Without capturing that return value into the `pid` variable, your program wouldn't be able to tell the parent and child apart!

---

## Problem 2: Process Interleaving and Strict Synchronization

### Part A: Interleaving and Concurrency

**The Goal:** Create two child processes (X and Y) that each run a loop for `N` iterations. In each iteration, they print their identity and iteration number, then sleep for a random amount of time.

**The Theory (Process Interleaving):**
When multiple processes are running on a computer concurrently, the Operating System's scheduler decides which process gets to use the CPU at any given microsecond. This is managed via **Time Slicing** (often using algorithms like Round Robin), where each process gets a tiny window of CPU time before being swapped out (a **Context Switch**) for another process.

Because we introduce a random sleep duration, we explicitly force the process to give up its CPU time slice and enter a "blocked" or "sleeping" state. The OS scheduler must then switch to the other available process.

This creates **process interleaving**. The output will look scrambled or "interleaved" (e.g., `X1, Y1, Y2, X2, X3, Y3`). Each time you run the program, the exact order of the output will be different. This non-deterministic behavior demonstrates the unpredictable nature of concurrent execution when there is no strict synchronization mechanism (like semaphores or mutexes) in place. 

**Implementation Details for C (`qs2.c`):**
To simulate this effectively in your C code:
1.  **Randomness (`rand()` & `srand()`):** Use `rand()` (from `<stdlib.h>`) to generate random sleep times. To ensure the sequence of random numbers is different every time you run the program, you must "seed" the random number generator. Because `fork()` duplicates the parent's memory, if you seed in the parent, both children will generate the exact same "random" numbers. To fix this, seed inside the child process using something unique to it, like its PID: `srand(time(NULL) ^ getpid());`.
2.  **Sleeping (`usleep()`):** Instead of `sleep()`, which waits for whole seconds (making the program run very slowly), use `usleep(microseconds)` (from `<unistd.h>`) to sleep for fractions of a second. This makes the interleaving much more apparent. For example, `usleep(rand() % 100000);` sleeps for up to 0.1 seconds.
3.  **Flushing output (`fflush(stdout)`):** When mixing `printf` and `fork()`, standard output is sometimes buffered, meaning lines from one process might be held back and printed all at once. Calling `fflush(stdout);` immediately after your `printf` forces the text to appear on the console exactly when it executes, giving you a true picture of the interleaving.

### Part B: Enforcing Strict Alternation (Synchronization)
**The Goal:** Modify the program so that Process Y cannot start iteration `i` until Process X has fully finished its iteration `i-1`.

**The Theory (Synchronization across loops):**
This is a classic synchronization problem. Process Y has a dependency on Process X. 

To solve this, we can use the same IPC mechanism as before: a **pipe**. We need a way for Process X to send a "signal" or a "token" to Process Y indicating "I have finished my iteration, you may now proceed with yours".

**How it works using a Pipe:**
1.  We create a single pipe connecting X (write end) to Y (read end).
2.  **Process X's Loop:** At the *end* of each of its iterations (let's say iteration `i-1`), X writes a dummy byte (a token) into the pipe.
3.  **Process Y's Loop:** At the *start* of each of its iterations (iteration `i`), Y tries to read a byte from the pipe.
    *   Because of the pipe's blocking property, if X hasn't finished its previous iteration yet (and thus hasn't written the token), Y will be forced to wait (block) on the read operation.
    *   As soon as X finishes and writes the token, Y reads it and is unblocked, allowing it to proceed with its iteration.

By establishing this relationship over a pipe in a loop, we enforce strict ordering: Y's current iteration must always wait for X's previous iteration to conclude.

---

## Problem 3: Inter-Process Communication (IPC) Mechanisms

**The Goal:** Implement three different applications using three distinct IPC mechanisms: Pipes, FIFOs (Named Pipes), and Message Queues.

### IPC Mechanisms Overview

1. **Pipes (Unnamed Pipes):**
   - **Concept:** A simple, unidirectional byte stream between related processes (parent and child).
   - **System Calls:** `pipe(int fd[2])`, `read()`, `write()`.
   - **Use Case:** Best for straightforward, 1-to-1 communication where processes share a common ancestor. For bidirectional communication, two pipes are required.

2. **FIFOs (Named Pipes):**
   - **Concept:** Similar to unnamed pipes, but they exist as actual files in the filesystem (e.g., `/tmp/myfifo`).
   - **System Calls:** `mkfifo(const char *pathname, mode_t mode)`, followed by standard file `open()`, `read()`, `write()`.
   - **Use Case:** Allows communication between unrelated processes. They persist even after processes terminate until explicitly unlinked.

3. **Message Queues (System V):**
   - **Concept:** A linked list of messages stored within the kernel, identified by a unique message queue identifier.
   - **System Calls:** `msgget()` (create/access), `msgsnd()` (send), `msgrcv()` (receive), `msgctl()` (control/delete).
   - **Use Case:** Supports complex communication patterns, including 1-to-many. Messages are strongly typed (via `mtype`), allowing processes to selectively receive specific messages (e.g., broadcast vs. targeted messages).

### Part A: Broadcasting Weather Information (Message Queue)
- **Design:** One broadcaster sends updates to multiple listeners.
- **Why Message Queue:** System V message queues allow attaching a `type` (`mtype`) to each message. The broadcaster can send the same weather update multiple times, each with a different `mtype` corresponding to a specific listener. Each listener calls `msgrcv()` requesting only its specific `mtype`, ensuring every listener gets a copy of the broadcast without interfering with others.

### Part B: Telephonic Conversation (Pipes)
- **Design:** Bidirectional communication between a caller (parent) and a receiver (child).
- **Why Pipes:** Since the caller and receiver are related (parent/child via `fork`), unnamed pipes are the most efficient mechanism. To achieve full-duplex (two-way) communication, we use two pipes: one for Caller → Receiver, and another for Receiver → Caller. They alternate reading and writing to simulate a conversation.

### Part C: Broadcast with Listener Replies (Named FIFOs)
- **Design:** One broadcaster sends updates to listeners; listeners can reply back.
- **Why Named FIFOs:** We create a separate FIFO for each direction and each listener (e.g., a broadcast FIFO and a reply FIFO per listener). `mkfifo` creates these named pipes in the filesystem. The broadcaster opens the broadcast FIFOs for writing and reply FIFOs for reading. Listeners do the opposite. This structure clearly separates the broadcast channel from the individual reply channels, allowing bidirectional, structured communication even if the processes were unrelated.

---

## Problem 4: CPU Scheduling Algorithms

**The Goal:** Build a scheduler that reads job execution profiles from a file and simulates three different CPU scheduling algorithms: **FCFS**, **Non-Preemptive Priority**, and **Round Robin (quantum=16)**. Compare the average waiting time and turnaround time across all three.

### The Theory (CPU Scheduling)

The **CPU Scheduler** is the OS component that decides which process in the **ready queue** gets to use the CPU next. Different scheduling algorithms lead to different performance characteristics. Understanding these trade-offs is fundamental to OS design.

#### Key Terminology

| Term | Definition |
|---|---|
| **Arrival Time** | The time at which a process enters the ready queue. |
| **CPU Burst** | A period of time during which a process is executing instructions on the CPU. |
| **I/O Burst** | A period of time during which a process is waiting for an I/O operation to complete (e.g., disk read). The CPU is free during this time. |
| **Burst Cycle** | A process alternates between CPU bursts and I/O bursts: `CPU → I/O → CPU → I/O → ... → CPU` |
| **Completion Time (CT)** | The time at which a process finishes all its bursts. |
| **Turnaround Time (TAT)** | Total time from arrival to completion: `TAT = CT - Arrival Time` |
| **Waiting Time (WT)** | Time spent waiting in the ready queue (not executing, not doing I/O): `WT = TAT - Total CPU Burst Time - Total I/O Burst Time` |
| **Response Time** | Time from arrival to the first time the process gets the CPU. |

#### Process State Transitions

```
                  ┌──────────────┐
    Arrival       │              │   CPU Burst
   ──────────────>│  Ready Queue │──────────────> Running
                  │              │                   │
                  └──────────────┘                   │
                        ▲                            │
                        │                            ▼
                        │          I/O Burst    ┌─────────┐
                        └──────────────────────│  I/O    │
                          (I/O complete)        │  Wait   │
                                                └─────────┘
```

When a process finishes a CPU burst:
- If it has more bursts, it goes to **I/O Wait** (the next burst is always I/O)
- If it has no more bursts, it **terminates**

When an I/O burst finishes:
- The process returns to the **Ready Queue** for its next CPU burst
- If there are no more bursts, it **terminates** (edge case: job ends with I/O)

---

### Algorithm 1: FCFS (First Come, First Served)

**Concept:** The simplest scheduling algorithm. Processes are executed in the exact order they arrive in the ready queue. It is **non-preemptive** — once a process starts its CPU burst, it runs to completion of that burst.

**How it works:**
1. All arrived processes are placed in a FIFO (First-In, First-Out) queue.
2. The process at the front of the queue gets the CPU.
3. It runs its entire current CPU burst without interruption.
4. After the CPU burst, if there's an I/O burst, the process goes to I/O and the next process in the queue gets the CPU.
5. When the I/O completes, the process re-enters the back of the ready queue.

**Pros:** Simple to implement, no starvation (every process eventually gets the CPU).
**Cons:** **Convoy Effect** — short processes stuck behind long ones get poor turnaround times. Not optimal for interactive systems.

**Example:**
```
Jobs: J1(arrival=0, CPU=32), J2(arrival=4, CPU=64)
Timeline: |---J1(0-32)---|---J2(32-96)---|
J1 WT = 0, J2 WT = 28 (waited from t=4 to t=32)
```

---

### Algorithm 2: Non-Preemptive Priority Scheduling

**Concept:** Each process has a priority number. The process with the **highest priority** (lowest priority number in our convention) is selected from the ready queue. Like FCFS, it is **non-preemptive** — the running process keeps the CPU until its current burst finishes.

**How it works:**
1. When the CPU is free, scan the ready queue.
2. Select the process with the lowest priority number (highest priority).
3. Ties are broken by arrival time (earlier arrival wins).
4. The selected process runs its entire CPU burst.
5. After finishing, the next highest-priority ready process is chosen.

**Pros:** Important/critical jobs get CPU first.
**Cons:** **Starvation** — low-priority processes may never get the CPU if high-priority processes keep arriving. Can be mitigated with **aging** (gradually increasing priority of waiting processes).

**Example:**
```
Jobs: J1(priority=3, arrival=0), J2(priority=1, arrival=4)
At t=32 (J1's burst done): J2 is picked next because priority 1 > priority 3
```

---

### Algorithm 3: Round Robin (RR)

**Concept:** A preemptive algorithm designed for time-sharing systems. Each process gets a fixed **time quantum** (time slice) of CPU time. If the process doesn't finish its CPU burst within the quantum, it is **preempted** (interrupted) and moved to the back of the ready queue.

**How it works:**
1. Processes are placed in a circular FIFO queue.
2. The process at the front gets the CPU for at most `quantum` time units.
3. **Case A:** If the CPU burst finishes within the quantum → process moves to I/O or terminates.
4. **Case B:** If the CPU burst is longer than the quantum → process is preempted after `quantum` units, remaining burst time is saved, and it's placed at the back of the ready queue.

**Time Quantum = 16** (as specified in the problem).

**Pros:** Fair — every process gets equal CPU time. Good for interactive systems. No starvation.
**Cons:** Higher context-switching overhead. Performance depends heavily on quantum size:
- **Too small quantum** → excessive context switches, poor throughput
- **Too large quantum** → degrades to FCFS

**Example:**
```
J1(CPU=32), J2(CPU=48), quantum=16
Timeline: |J1(16)|J2(16)|J1(16)|J2(16)|J2(16)|
J1 gets preempted after first 16 units, J2 gets a turn, then J1 finishes, then J2 finishes.
```

---

### Implementation Guide (`qs4.cpp`)

#### 1. Input File Format

Each line represents one job:
```
<Job-id> <priority> <arrival-time> <CPU-burst(1)> <I/O-burst(1)> <CPU-burst(2)> ... -1
```

Bursts alternate: CPU, I/O, CPU, I/O, ..., and the profile ends with `-1`.
A job may end with either a CPU burst or an I/O burst.

**Example:** `2 3 0 32 64 16 32 -1` means:
- Job ID: 2, Priority: 3, Arrival: 0
- CPU(32) → I/O(64) → CPU(16) → I/O(32)

#### 2. Data Structures

```cpp
struct Burst {
  char type; // 'C' for CPU, 'I' for I/O
  int duration;
};

struct Job {
  int id;
  int priority;
  int arrival_time;
  vector<Burst> bursts;  // alternating CPU and I/O
};

struct JobState {
  // ... runtime state for simulation
  int current_burst_idx;  // which burst we're on
  int remaining;          // remaining time in current burst
  int completion_time, turnaround_time, waiting_time;
  int last_ready_time;    // when job last entered the ready queue
};
```

#### 3. Core Simulation Pattern

All three algorithms follow the same event-driven simulation loop:

```
while (not all jobs done):
    1. Add newly arrived jobs to the ready queue
    2. Process completed I/O bursts (move jobs back to ready queue)
    3. If ready queue is empty → fast-forward time to next event
    4. Select a job from the ready queue (algorithm-specific selection)
    5. Run the job's CPU burst (fully for FCFS/Priority, up to quantum for RR)
    6. After burst:
       - If job has more bursts → queue I/O burst
       - If job is done → record completion time
    7. Handle new arrivals and I/O completions that occurred during the burst
```

#### 4. Key Implementation Details

**Waiting Time Tracking:**
- When a job enters the ready queue, record `last_ready_time = current_time`
- When a job is picked from the ready queue, accumulate: `waiting_time += (current_time - last_ready_time)`
- This correctly handles multiple ready-queue entries (after I/O or preemption)

**I/O Queue (min-heap):**
- Use a priority queue ordered by I/O completion time
- When an I/O completes, advance `current_burst_idx` and check:
  - If the job is finished → record completion
  - Otherwise → add to ready queue with the next CPU burst

**Fast-Forward:**
When the ready queue is empty but jobs are still pending:
- Find the minimum of: next job arrival time, next I/O completion time
- Jump time forward to that event (avoids busy-waiting)

**Edge Case — Jobs Ending with I/O:**
A job's burst sequence might end with an I/O burst (e.g., `CPU→I/O→CPU→I/O`).
When the final I/O completes:
- The job is finished — record `completion_time = I/O_end_time`
- **This is a common bug** to miss (only checking completion after CPU bursts)

#### 5. Algorithm-Specific Ready Queue Selection

| Algorithm | Selection Rule |
|---|---|
| **FCFS** | `queue<int>` — FIFO, pick `front()` |
| **Priority** | Scan all ready jobs, pick the one with lowest priority number. Tie-break by arrival time. |
| **Round Robin** | `queue<int>` — FIFO like FCFS, but run for `min(quantum, remaining)`. If preempted, push back to queue. |

#### 6. Computing Final Metrics

```cpp
Turnaround Time = Completion Time - Arrival Time
Waiting Time = (accumulated from ready-queue waits)
// Equivalently: WT = TAT - Total CPU burst time - Total I/O burst time
```

#### 7. Comparison Output

After running all three algorithms on the same job set, compare:
- **Average TAT** — lower is better (jobs finish sooner)
- **Average WT** — lower is better (less idle waiting)

Typically:
- **FCFS**: Simplest, but convoy effect hurts short jobs
- **Priority**: Good for critical jobs, but can starve low-priority ones
- **Round Robin**: Fairest, but quantum tuning is critical

---

## Problem 5: Deadlock Avoidance (Banker's Algorithm)

**The Goal:** Write a program to determine if a system is in a "safe state" and whether a specific resource request from a process should be granted without leading to a deadlock.

### The Theory (Banker's Algorithm)
In an operating system, processes request resources (like memory, printers, CPU cycles). If resources are granted blindly, the system might enter a **deadlock** (where processes are waiting on each other indefinitely). 

The **Banker's Algorithm** avoids deadlock by simulating the allocation of predetermined maximum possible amounts of all resources, and then making a "safe-state" check to test for possible deadlock conditions for all other pending activities, before deciding whether allocation should be allowed to continue.

**Key Matrices/Vectors in Banker's Algorithm:**
1. **Available (Vector):** The number of available instances of each resource type.
2. **Max (Matrix):** The maximum demand of each process. `Max[i][j] = k` means process `i` may request at most `k` instances of resource type `j`.
3. **Allocation (Matrix):** The number of resources of each type currently allocated to each process.
4. **Need (Matrix):** The remaining resource need of each process. `Need[i][j] = Max[i][j] - Allocation[i][j]`.

**Safe State:** A state is considered safe if there exists a sequence of all processes `<P1, P2, ..., Pn>` such that for each `Pi`, the resources that `Pi` can still request can be satisfied by the currently available resources plus the resources held by all previously finished processes in the sequence.

**Resource-Request Algorithm:**
When a process `Pi` requests a set of resources (`Request_i`):
1. Check if `Request_i <= Need_i`. If not, raise an error (process exceeded maximum claim).
2. Check if `Request_i <= Available`. If not, `Pi` must wait (resources not available).
3. Pretend to allocate the resources:
   - `Available = Available - Request_i`
   - `Allocation_i = Allocation_i + Request_i`
   - `Need_i = Need_i - Request_i`
4. Run the Safety Algorithm on this new state.
   - If the new state is safe, formally grant the request.
   - If the new state is unsafe, restore the old state (undo step 3) and `Pi` must wait.

### Implementation Details for C (`qs5.c`)
Your program needs to read from a file and parse a specific format. Here are some tips for implementation:

1. **File Parsing (`fgets` and `strtok`):**
   - The input format is slightly complex, using mixed text and numbers, and commas as delimiters. 
   - Read the file line-by-line using `fgets()`. Then, use `strtok()` with commas `","` and spaces `" "` as delimiters to extract the numbers, ignoring the text labels. You can use `atoi()` to convert the token strings to integers.
   - Alternatively, you can use `fscanf` if you carefully match the string literals, but `strtok` is generally safer for mixed formats.

2. **Data Structures:**
   - Use arrays to store your matrices. Since this is C, you can define a `MAX_PROCESSES` (e.g., 100) and `MAX_RESOURCES` (e.g., 100) to keep things simple:
     ```c
     int available[MAX_RESOURCES];
     int max[MAX_PROCESSES][MAX_RESOURCES];
     int allocation[MAX_PROCESSES][MAX_RESOURCES];
     int need[MAX_PROCESSES][MAX_RESOURCES];
     ```

3. **The "Present Situation" Generation:**
   - The problem asks you to generate the present situation (Allocation matrix) based on a sequence.
   - When generating the initial `Allocation` matrix, ensure you also calculate the initial `Need` matrix (`Need[i][j] = Max[i][j] - Allocation[i][j]`).
   - Also, update the `Available` array by subtracting the initially allocated resources from the total instances of each resource.

4. **The Safety Algorithm Loop:**
   - You need a `bool finish[MAX_PROCESSES]` array initialized to `false`.
   - You need a `work[MAX_RESOURCES]` array initialized to a copy of `available`.
   - Loop through all processes. Find a process `i` such that `!finish[i]` AND `need[i][j] <= work[j]` for all resources `j`.
   - If found, simulate it finishing: `work[j] += allocation[i][j]`, and `finish[i] = true`. Add `i` to your `safe_sequence` array.
   - Repeat this until no such process can be found.
   - If all `finish[i]` are true, it's a safe state! You can print the `safe_sequence`.

5. **Handling Interactive Requests:**
   - Wrap the request logic in an infinite `while(1)` loop. 
   - Prompt the user for the sequence `<pid r0 r1 r2 ...>`.
   - Apply the Resource-Request algorithm:
     1. Bounds checking.
     2. Pretend allocation (temporarily modify `Available`, `Allocation`, and `Need`).
     3. Run the Safety check.
   - If safe, tell the user the request is granted and print the safe sequence. Keep the matrix changes.
   - If unsafe, tell the user it's denied, REVERT the matrix changes back to their previous state, and prompt again.
   - Stop the loop when all processes have finished (i.e., when `Need[i][j] == 0` for all `i, j`).
