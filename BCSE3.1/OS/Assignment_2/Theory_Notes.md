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
