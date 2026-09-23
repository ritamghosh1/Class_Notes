# Question 1: Boot-level Password Verification System

## 1. What You Have to Do
You are tasked with simulating a BIOS-like password verification system using assembly language (MASM). The program must:
1. Accept password input from the user without echoing (displaying) the typed characters on the screen.
2. Compare the entered password against a hardcoded password stored in the program.
3. Keep track of the number of attempts and allow a maximum of 3 retries.
4. If the user fails 3 times, lock the system.
5. Crucially, you must use **BIOS interrupts** for handling keyboard input instead of standard DOS interrupts.

## 2. How to Do It (The Approach)
1. **Data Definition**: Store the hardcoded password (e.g., `"secret"`), prompt messages, failure messages, and success messages in the data segment. Also, allocate a buffer for the user's input and a counter for the attempts (initialized to `3`).
2. **User Input Handling (BIOS Interrupt)**: 
   - Use BIOS Interrupt **`INT 16h`** with **`AH = 00h`**. This reads the next keystroke from the keyboard buffer. It waits until a key is pressed.
   - Since `INT 16h` only reads the key and does not automatically print it to the screen (unlike DOS `INT 21h, AH=01h`), it perfectly achieves the "hidden password input (no echo)" requirement.
   - We collect these characters in a loop until the `Enter` key (ASCII `0Dh`) is pressed.
3. **Comparison**:
   - Once `Enter` is pressed, use string comparison instructions (`REPE CMPSB`) to compare the input buffer with the hardcoded password.
4. **Retry Logic**:
   - If they match, grant access and exit.
   - If they don't match, decrement the attempts counter. If the counter reaches 0, trigger the lock sequence.
5. **System Lock Simulation**:
   - If attempts run out, display a lock message and enter an infinite loop with the `HLT` (halt) instruction to simulate a frozen/locked system.

## 3. The Theory Portion
### BIOS vs. DOS Interrupts
- **DOS Interrupts (`INT 21h`)**: These are higher-level software interrupts provided by the Disk Operating System (DOS). They handle file operations, standard I/O, etc.
- **BIOS Interrupts (`INT 10h`, `INT 16h`, etc.)**: Basic Input/Output System (BIOS) interrupts operate at a lower level, communicating more directly with the hardware. `INT 16h` handles keyboard hardware services.

### Keyboard BIOS Interrupt `INT 16h`
- When `AH = 00h` is loaded and `INT 16h` is called, the BIOS waits for a key to be pressed. 
- Once a key is pressed, it returns the **ASCII character** in the `AL` register and the hardware **Scan Code** in the `AH` register.
- Because this reads directly from the keyboard controller without routing through DOS's standard input buffer, the character is not echoed to the display. 

### String Operations in MASM
- `CMPSB` (Compare String Byte): Compares the byte at `DS:SI` with the byte at `ES:DI`.
- `REPE` (Repeat while Equal): A prefix that repeats the string instruction (like `CMPSB`) up to `CX` times, as long as the compared elements are equal.
- `CLD`: Clears the direction flag, ensuring string operations process from left to right (incrementing `SI` and `DI`).

## 4. Why This Approach?
Using BIOS interrupts for early boot-level tasks is necessary because, at the boot stage (when the BIOS is executing), the Operating System (like DOS, Windows, or Linux) has not yet been loaded into memory. Therefore, high-level OS-provided interrupts (like `INT 21h`) are unavailable. Simulating this teaches you how early software secures the hardware using fundamental ROM-BIOS routines before OS execution begins.

## 5. Code Implementation in MASM

```assembly
.model small
.stack 100h

.data
    prompt_msg      db 'Enter password: $'
    success_msg     db 10, 13, 'Access Granted! System Booting...', 10, 13, '$'
    fail_msg        db 10, 13, 'Access Denied! Incorrect Password.', 10, 13, '$'
    lock_msg        db 10, 13, 'SYSTEM LOCKED! Max retries exceeded.', 10, 13, '$'
    
    hardcoded_pass  db 'secret'
    pass_len        equ $ - hardcoded_pass
    
    input_buffer    db 20 dup(0)
    attempts        db 3

.code
main proc
    ; Initialize data segments
    mov ax, @data
    mov ds, ax
    mov es, ax      ; ES needed for string comparison (cmpsb)

retry_loop:
    ; Check if attempts reached 0
    cmp attempts, 0
    je system_lock

    ; Display prompt
    mov ah, 09h
    lea dx, prompt_msg
    int 21h

    ; Initialize buffer pointer and counter
    lea di, input_buffer
    mov cx, 0       ; Character count

input_loop:
    ; Read character using BIOS interrupt 16h
    mov ah, 00h
    int 16h         ; AL = ASCII character

    cmp al, 0Dh     ; Check if ENTER key is pressed (Carriage Return)
    je check_password

    cmp al, 08h     ; Handle backspace (optional, but good practice)
    je handle_backspace

    ; Store character in buffer and increment pointer & counter
    mov [di], al
    inc di
    inc cx
    jmp input_loop

handle_backspace:
    cmp cx, 0       ; If nothing to backspace, ignore
    je input_loop
    dec di          ; Move pointer back
    dec cx          ; Decrement count
    jmp input_loop

check_password:
    ; Check if lengths match first
    cmp cx, pass_len
    jne password_incorrect

    ; Compare strings byte by byte
    lea si, hardcoded_pass
    lea di, input_buffer
    mov cx, pass_len
    cld             ; Clear direction flag (auto-increment SI and DI)
    repe cmpsb      ; Compare CX bytes at DS:SI and ES:DI
    jne password_incorrect

    ; Passwords match -> Success
    mov ah, 09h
    lea dx, success_msg
    int 21h
    jmp exit_program

password_incorrect:
    ; Display fail message
    mov ah, 09h
    lea dx, fail_msg
    int 21h

    ; Decrement attempts and try again
    dec attempts
    jmp retry_loop

system_lock:
    ; Display lock message
    mov ah, 09h
    lea dx, lock_msg
    int 21h

    ; Simulate system lock (infinite loop)
lock_halt:
    cli             ; Disable interrupts
    hlt             ; Halt processor
    jmp lock_halt   ; Loop indefinitely to "lock"

exit_program:
    ; Terminate program normally
    mov ah, 4Ch
    int 21h
main endp
end main
```
