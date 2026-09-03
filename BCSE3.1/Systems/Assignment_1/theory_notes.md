# System Programming Lab - Assignment 1: Theory Notes

## 📚 Prerequisites: 8086 Assembly Fundamentals

### Memory Model & Segments
- **`.MODEL SMALL`**: Code and data each fit in one 64KB segment.
- **`.STACK 100H`**: Allocates 256 bytes for the stack.
- **`.DATA`**: Declares initialized/uninitialized data variables.
- **`.CODE`**: Contains executable instructions.
- Segments are loaded via `MOV AX, @DATA` → `MOV DS, AX` at program start.

### Key Registers
| Register | Purpose |
|----------|---------|
| **AX** (AH:AL) | Accumulator — used in arithmetic, MUL, DIV, I/O |
| **BX** (BH:BL) | Base register — used for addressing & temp storage |
| **CX** (CH:CL) | Counter — loop counter for `LOOP`, shift count |
| **DX** (DH:DL) | Data — I/O port addressing, MUL/DIV overflow |
| **SI** | Source Index — points to source in string/memory ops |
| **DI** | Destination Index — points to destination |
| **SP** | Stack Pointer — top of stack |
| **BP** | Base Pointer — stack frame access |

### DOS Interrupts (INT 21H)
| AH Value | Function |
|----------|----------|
| `01H` | Read character from keyboard → AL |
| `02H` | Display character in DL |
| `09H` | Display '$'-terminated string at DS:DX |
| `4CH` | Terminate program (return to DOS) |

---

## Q1: Block Transfer with Transformation

### 📝 Problem
Transfer 10 bytes from memory `3000H` to `4000H`. Before storing each byte: **multiply by 5**, then **add 10**.

### 🔑 Key Concepts

#### `MUL` Instruction
- **`MUL BL`** performs **unsigned** multiplication: `AX = AL × BL`
- The multiplicand is always in `AL` (for byte multiplication).
- Result is stored in `AX` (16-bit), but for small numbers only `AL` matters.

#### `LOOP` Instruction
- Decrements `CX` by 1.
- Jumps to the target label if `CX ≠ 0`.
- Equivalent to: `DEC CX` + `JNZ label`.

### 🔄 How the Code Works

```
For each of the 10 elements:
  1. Load byte from [SI] into AL
  2. Multiply:  AL = AL × 5     (MUL BL, where BL=5)
  3. Add:       AL = AL + 10    (ADD AL, 0AH)
  4. Store AL into [DI]
  5. Increment SI and DI
  6. LOOP decrements CX, repeats if CX ≠ 0
```

#### Example Trace
| Source (3000H) | ×5 | +10 | Dest (4000H) |
|:-:|:-:|:-:|:-:|
| 01H (1) | 05 | 15 | 0FH |
| 02H (2) | 10 | 20 | 14H |
| 03H (3) | 15 | 25 | 19H |
| 0AH (10) | 50 | 60 | 3CH |

### ⚠️ Overflow Note
If `AL × 5 + 10 > 255`, the result wraps around (byte overflow). For the given data (max 10), the max result is `10×5+10 = 60`, so no overflow occurs.

---

## Q2: Zig-Zag Array Ordering

### 📝 Problem
Arrange 20 numbers so that they alternate: `a[0] < a[1] > a[2] < a[3] > a[4] ...`

### 🔑 Key Concepts

#### Zig-Zag / Wave Sort Algorithm
This is a **single-pass O(n)** algorithm — no full sort needed:
- At **even indices** (0, 2, 4...): if `a[i] > a[i+1]`, **swap** them (we need `a[i] < a[i+1]`).
- At **odd indices** (1, 3, 5...): if `a[i] < a[i+1]`, **swap** them (we need `a[i] > a[i+1]`).

This works because:
- A swap at position `i` only affects `a[i]` and `a[i+1]`.
- The property already established at `i-1` is preserved because the swap at `i` pushes the larger/smaller element to the correct side.

#### `TEST` Instruction
- **`TEST BX, 01H`** performs a bitwise AND without storing the result — only sets flags.
- If the least significant bit of BX is 1, the Zero Flag (ZF) is cleared → the index is **odd**.
- If ZF is set → the index is **even**.

### 🔄 How the Code Works

```
1. Copy 20 elements from ARR to RESULT (at 4000H)
2. For i = 0 to 18:
     if i is even:
       if RESULT[i] > RESULT[i+1] → swap
     if i is odd:
       if RESULT[i] < RESULT[i+1] → swap
```

#### Example Trace (first 6 elements)
```
Input:  [15, 03, 22, 07, 19, 01, ...]

i=0 (even): 15 > 03? YES → swap → [03, 15, 22, 07, 19, 01]
i=1 (odd):  15 > 22? NO  → swap → [03, 22, 15, 07, 19, 01]
i=2 (even): 15 > 07? YES → swap → [03, 22, 07, 15, 19, 01]
i=3 (odd):  15 > 19? NO  → swap → [03, 22, 07, 19, 15, 01]
i=4 (even): 15 > 01? YES → swap → [03, 22, 07, 19, 01, 15]

Result: 3 < 22 > 7 < 19 > 1 < 15 ✓ (zig-zag!)
```

---

## Q3: Hexadecimal to ASCII Conversion

### 📝 Problem
Convert a hexadecimal byte (e.g., `4BH`) into its ASCII string representation (`"4B"`).

### 🔑 Key Concepts

#### Nibble Extraction
A byte has **two nibbles** (4 bits each):
```
  Byte:    4BH  =  0100 1011
  Upper nibble:    0100      = 4
  Lower nibble:         1011 = B (11)
```

- **Upper nibble**: `SHR AL, 4` (shift right by 4 bits)
- **Lower nibble**: `AND AL, 0FH` (mask out upper bits)

#### ASCII Encoding Rules
| Nibble Value | ASCII Code | Conversion |
|:---:|:---:|---|
| 0–9 | 30H–39H ('0'–'9') | Add `30H` |
| A–F | 41H–46H ('A'–'F') | Add `37H` (because `0AH + 37H = 41H = 'A'`) |

#### `SHR` (Shift Right)
- `SHR AL, 4` shifts AL right by 4 bit positions, filling the upper bits with 0.
- On strict 8086, immediate shift count > 1 requires using CL: `MOV CL, 4` / `SHR AL, CL`.

### 🔄 How the Code Works

```
1. Load hex byte (e.g., 4BH) into AL
2. Extract upper nibble:
     SHR AL, 4  →  AL = 04H
     Call NIBBLE_TO_ASCII → AL = '4' (34H)
     Store as first character
3. Extract lower nibble:
     AND AL, 0FH → AL = 0BH
     Call NIBBLE_TO_ASCII → AL = 'B' (42H)
     Store as second character
4. Display the two-character ASCII result: "4B"
```

#### NIBBLE_TO_ASCII Logic
```
if nibble <= 9:
    return nibble + 30H    ; '0' to '9'
else:
    return nibble + 37H    ; 'A' to 'F'
```

---

## Q4: Basic Calculator

### 📝 Problem
Read two single-digit numbers and an operator (+, -, *, /), perform the operation, and display the decimal result.

### 🔑 Key Concepts

#### ASCII to Number Conversion
- User input via `INT 21H, AH=01H` returns the **ASCII code** in AL.
- `'5'` = `35H`. To get the numeric value: `SUB AL, 30H` → `AL = 5`.

#### Arithmetic Instructions
| Instruction | Operation | Notes |
|---|---|---|
| `ADD AL, BL` | AL = AL + BL | Sets Carry Flag on overflow |
| `SUB AL, BL` | AL = AL - BL | Result can be negative (two's complement) |
| `MUL BL` | AX = AL × BL | Unsigned multiply, result in AX |
| `DIV BL` | AL = AX / BL, AH = AX mod BL | **Must clear AH** before dividing a byte! |

#### Division Pitfall
Before `DIV BL`, you **must** ensure `AH = 0` (via `XOR AH, AH`), otherwise the CPU divides the full 16-bit AX by BL, giving wrong results or a divide overflow exception.

#### Decimal Output (Number → ASCII)
To display a multi-digit number, repeatedly divide by 10 and push remainders onto the stack:
```
Number: 60
  60 / 10 = 6, remainder 0  → push '0'
   6 / 10 = 0, remainder 6  → push '6'
Pop and print: '6' then '0' → displays "60"
```

### 🔄 How the Code Works

```
1. Read first digit  → convert from ASCII → store as NUM1
2. Read operator     → store as OPER
3. Read second digit → convert from ASCII → store as NUM2
4. Compare OPER with '+', '-', '*', '/' → jump to handler
5. Perform arithmetic → result in AX
6. Convert AX to decimal string via divide-by-10 loop
7. Print digits in correct order (using stack reversal)
```

#### Handling Negative Results (Subtraction)
- If `NUM1 < NUM2`, the result is negative (two's complement).
- Check the sign bit (`TEST BX, 8000H`), print `'-'`, then `NEG BX` to make it positive for display.

---

## Q5: String Operations Library

### 📝 Problem
Implement three string functions:
- **STRLEN**: Return length of a `'$'`-terminated string
- **STRCMP**: Compare two strings for equality
- **STRREV**: Reverse a string in place

### 🔑 Key Concepts

#### String Termination
MASM/DOS uses `'$'` (24H) as the string terminator (unlike C's null `'\0'`). All our functions scan for `'$'` to find string boundaries.

#### Procedure Calling Convention
```asm
CALL STRLEN      ; Pushes return address onto stack, jumps to STRLEN
...
STRLEN PROC      ; Procedure definition
    ...
    RET          ; Pops return address, returns to caller
STRLEN ENDP
```

#### Register Preservation
Good practice: **PUSH** registers at the start of a procedure, **POP** them before `RET`. This prevents the caller's registers from being clobbered.

### 🔄 How Each Function Works

---

#### a) STRLEN — String Length

**Algorithm**: Linear scan from start to `'$'` terminator.

```
Input:  SI → "Hello, World!$"
CX = 0

Loop:
  [SI] = 'H' ≠ '$' → CX=1, SI++
  [SI] = 'e' ≠ '$' → CX=2, SI++
  ...
  [SI] = '!' ≠ '$' → CX=13, SI++
  [SI] = '$' → DONE

Output: CX = 13
```

**Time Complexity**: O(n) where n = string length.

---

#### b) STRCMP — String Compare

**Algorithm**: Compare character-by-character until a mismatch or both reach `'$'`.

```
Input:  SI → "Hello$", DI → "Hello$"

Loop:
  [SI]='H', [DI]='H' → equal, not '$', continue
  [SI]='e', [DI]='e' → equal, not '$', continue
  ...
  [SI]='$', [DI]='$' → equal AND '$' → STRINGS ARE EQUAL

Output: AX = 0 (equal)
```

```
Input:  SI → "Hello$", DI → "Different$"

Loop:
  [SI]='H', [DI]='D' → NOT equal → STRINGS DIFFER

Output: AX = 1 (not equal)
```

---

#### c) STRREV — String Reverse (In-Place)

**Algorithm**: Two-pointer technique — swap characters from the front and back, moving inward.

```
Input:  SI → "ABCDEF$"

Step 1: Find end → DI points to 'F' (last char before '$')

Step 2: Swap from both ends inward:
  Swap [SI]='A' ↔ [DI]='F' → "FBCDEA$", SI++, DI--
  Swap [SI]='B' ↔ [DI]='E' → "FECDBA$"  wait...
  Actually:
    "ABCDEF" → swap A↔F → "FBCDEA"
                swap B↔E → "FECDBA"
                swap C↔D → "FEDCBA"
  SI meets DI → DONE

Output: "FEDCBA$"
```

**Time Complexity**: O(n/2) ≈ O(n), **Space**: O(1) — in-place, no extra memory.

### ⚠️ Important Notes on STRREV
- `DEC DI` after finding `'$'` ensures DI points to the **last character**, not the terminator.
- The `CMP SI, DI` + `JAE` handles both even and odd length strings correctly.
  - Odd length: pointers meet at the middle character (no swap needed).
  - Even length: pointers cross each other.

---

## 📖 General Theory: Key 8086 Concepts Used

### Addressing Modes
| Mode | Example | Description |
|---|---|---|
| Immediate | `MOV AL, 05H` | Operand is a constant |
| Register | `MOV AX, BX` | Operand is in a register |
| Direct | `MOV AL, [3000H]` | Address is given directly |
| Register Indirect | `MOV AL, [SI]` | Address is in a register |
| Indexed | `MOV AL, [SI+1]` | Register + displacement |

### Conditional Jumps Used
| Instruction | Meaning | Condition (Flags) |
|---|---|---|
| `JE` / `JZ` | Jump if Equal / Zero | ZF = 1 |
| `JNE` / `JNZ` | Jump if Not Equal | ZF = 0 |
| `JBE` / `JNA` | Jump if Below or Equal (unsigned) | CF=1 or ZF=1 |
| `JAE` / `JNB` | Jump if Above or Equal (unsigned) | CF = 0 |
| `JB` / `JNAE` | Jump if Below (unsigned) | CF = 1 |

### Stack Operations
| Instruction | Effect |
|---|---|
| `PUSH AX` | SP -= 2; [SS:SP] = AX |
| `POP AX` | AX = [SS:SP]; SP += 2 |
| `CALL proc` | Pushes IP (return address), jumps to proc |
| `RET` | Pops IP, returns to caller |

### The `ORG` Directive
- `ORG 3000H` sets the **location counter** to offset `3000H`.
- The next variable declared will be placed at that offset in the data segment.
- Used in Q1 and Q2 to simulate specific memory addresses as required by the problem.

---

## 🛠️ How to Assemble and Run (DOSBox + MASM)

```bash
# Step 1: Assemble
MASM q1.asm;

# Step 2: Link
LINK q1.obj;

# Step 3: Run
q1.exe

# Or use an emulator like emu8086 for step-by-step debugging
```

---

# 📝 Question 6: String Reversal and Common Substring Detection

## 📖 Problem Statement
Write a MASM program to read two strings, reverse the first string, and check if there is any common substring present between them. If a common substring is found, it should be printed.

## 🧠 Methodology

This problem involves **Input Acquisition**, **String Reversal**, and **Nested Character Matching**.

1. **Input Acquisition (Buffered Input):**
   - We utilize DOS interrupt `INT 21H, AH = 0AH` to capture two dynamic strings entered by the user from the keyboard (`BUF1` and `BUF2`).
   - A sub-routine (`READ_STRING`) formats the end of the buffered input by replacing the terminal Carriage Return (`0DH`) with the standard DOS string terminator (`$`).

2. **String Reversal (`STRREV`):**
   - We utilize a classic two-pointer technique to reverse the first string (`BUF1`) in place.
   - **Pointer 1 (`SI`)** points to the start of the string, while **Pointer 2 (`DI`)** iterates forward until it locates the `$` terminator, then steps backward by one to point to the final character.
   - We enter a loop where the characters at `SI` and `DI` are swapped. `SI` is incremented and `DI` is decremented. 
   - The loop terminates when `SI` meets or crosses `DI` (`JAE REVERSE_DONE`), indicating the string is fully reversed.

3. **Substring Detection & Printing:**
   - To check if the reversed string shares any common substring with the second string, we use an $O(M \times N)$ nested loop structure.
   - **Outer Loop (`SI`):** Iterates through each character of the reversed `STR1`.
   - **Inner Loop (`DI`):** For each character in `STR1`, it scans the entirety of `STR2`.
   - If a match is found (`CMP AL, BL`), we immediately jump to a success handler (`FOUND_MATCH`).
   - The success handler then loops through both strings starting from the matching characters (`SI` and `DI`) and prints characters sequentially to the console using `INT 21H, AH = 02H` as long as they continue to match. 
   - If they differ, the printing stops and the program exits.

## 💻 Code Explanation

### 1. Reversing the String (`STRREV`)
```assembly
    MOV DI, SI
FIND_END:
    MOV AL, [DI]
    CMP AL, '$'
    JE FOUND_END
    INC DI
    JMP FIND_END

FOUND_END:
    DEC DI                   
```
- First, we scan `STR1` to find its exact end. `DI` increments until the `$` is found, then backs up by one. Now `SI` points to the start, and `DI` points to the end.

```assembly
REVERSE_LOOP:
    CMP SI, DI
    JAE REVERSE_DONE         

    MOV AL, [SI]             
    MOV BL, [DI]
    MOV [SI], BL
    MOV [DI], AL

    INC SI
    DEC DI
    JMP REVERSE_LOOP
```
- We swap the bytes in memory. `AL` gets the front character, `BL` gets the back character, and we write them to opposite locations. The pointers then move inward.

### 2. Searching for Common Substrings
```assembly
    LEA SI, BUF1 + 2       ; Outer loop pointer (Reversed String)
OUTER_1:
    MOV AL, [SI]
    CMP AL, '$'            ; Are we done scanning the first string?
    JE NOT_FOUND

    LEA DI, BUF2 + 2       ; Inner loop pointer (Second String)
OUTER_2:
    MOV BL, [DI]
    CMP BL, '$'            
    JE NEXT_OUTER_1        ; If second string ends, move to next char in first string

    CMP AL, BL             ; Compare character
    JE FOUND_MATCH         ; Match found!

    INC DI                 ; Move to next char in second string
    JMP OUTER_2
```
- We load the data block of `BUF1` starting at index 2 (skipping the DOS buffer headers). 
- `SI` holds the current character of the reversed string. We load `DI` with the start of the second string and scan it entirely looking for `AL == BL`. 

### 3. Printing the Match
```assembly
FOUND_MATCH:
    MOV BP, SI
    MOV BX, DI
PRINT_MATCH_LOOP:
    MOV AL, [BP]           ; Char from reversed STR1
    MOV DL, [BX]           ; Char from STR2
    
    CMP AL, '$'            ; Reached end of STR1?
    JE EXIT_PROG
    CMP DL, '$'            ; Reached end of STR2?
    JE EXIT_PROG
    
    CMP AL, DL             ; Do they still match?
    JNE EXIT_PROG          ; If they differ, we are done printing

    MOV AH, 02H            ; Print the matching character
    INT 21H

    INC BP
    INC BX
    JMP PRINT_MATCH_LOOP
```
- Once a match is detected, temporary registers `BP` and `BX` are used to iterate through both strings. As long as the characters match, they are printed to the console sequentially.
