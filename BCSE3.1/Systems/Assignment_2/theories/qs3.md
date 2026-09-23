# Question 3: FCFS Disk Scheduling Algorithm

## 1. What You Have to Do
You are tasked with writing a MASM assembly program that simulates the **First-Come-First-Served (FCFS)** disk scheduling algorithm. The program must:
1. Accept the initial position of the disk head.
2. Accept the number of track requests ($n$).
3. Read the sequence of track requests from the user.
4. Calculate and **print the head movement (seek time) for each individual step**.
5. Calculate and **print the total head movement** by summing the absolute differences between consecutive tracks.
6. Calculate and **print the average head movement** (`total / n`).

## 2. How to Do It (The Approach)
1. **User Input**: Similar to Q4, we need to read multi-digit numbers for the initial head position, the number of requests, and the individual track numbers.
2. **Data Storage**: We store the initial head position in a variable and the requests in an array (e.g., `requests dw 100 dup(0)`).
3. **FCFS Algorithm**: 
   - Initialize a `total_movement` accumulator to 0.
   - Keep track of the `previous_position` (initially set to the `initial_head`).
   - Loop through the array of requests. For each request, calculate the absolute difference: `|current_request - previous_position|`.
   - Print the movement for this specific step.
   - Add this difference to `total_movement`.
   - Update `previous_position` to be the `current_request`.
4. **Absolute Value in Assembly**: We subtract the previous position from the current position. If the result is negative (indicated by the Sign Flag), we use the `NEG` instruction to invert the sign (making it positive).
5. **Averaging**: After the loop finishes, we divide the `total_movement` by `n` using the `DIV` instruction and print the quotient.

## 3. The Theory Portion
### What is a "Track Request"?
In magnetic hard disk drives (HDDs), data is stored on circular **tracks** (or cylinders). A **track request** is a request by the operating system to read or write data located on a specific track. 
- **Range of Tracks**: For standard academic textbook problems (like those from Galvin's OS book), the track range is usually **0 to 199** (200 tracks total). However, in modern HDDs, there are tens of thousands of tracks. Our program handles 16-bit integers, so it can support tracks up to 65,535.

### FCFS Algorithm
FCFS is the simplest disk scheduling algorithm. It processes requests exactly in the order they arrive in the disk queue. 
- **Advantage**: It is fair and easy to implement.
- **Disadvantage**: It doesn't optimize for seek time, often leading to a high total head movement (the "convoy effect").

### Absolute Difference (`ABS`) in Assembly
Assembly doesn't have a built-in `abs()` function. To find `|A - B|`:
1. Subtract `B` from `A` (`SUB AX, BX`).
2. Check if the result is negative using a conditional jump like `JNS` (Jump if Not Sign / Jump if positive).
3. If it is negative, the code falls through to the `NEG AX` instruction, which performs a two's complement negation, effectively turning `-5` into `5`.

### Division for Average
To find the average, we use the `DIV` instruction. `DIV BX` divides the 32-bit number in `DX:AX` by `BX`. The quotient is stored in `AX` and the remainder in `DX`. We must ensure `DX` is 0 before dividing to prevent divide overflow errors.

## 4. Why This Approach?
This approach introduces conditional mathematical logic (absolute values) inside a loop. It demonstrates how algorithms that are visually intuitive (like hopping between tracks on a disk) translate into linear mathematical accumulations at the processor level. It also practices `DIV` which is often tricky in 16-bit assembly.

## 5. Code Implementation in MASM

```assembly
.model small
.stack 100h

.data
    prompt_head   db 'Enter initial head position: $'
    prompt_n      db 'Enter number of requests: $'
    prompt_req    db 'Enter track request: $'
    msg_step      db 10, 13, 'Movement to track: $'
    msg_step_mov  db ' | Seek time: $'
    msg_total     db 10, 13, 10, 13, 'Total head movement: $'
    msg_avg       db 10, 13, 'Average head movement: $'
    newline       db 10, 13, '$'
    
    initial_head  dw ?
    n             dw ?
    requests      dw 100 dup(0)
    total_mov     dw 0

.code
main proc
    ; Initialize data segment
    mov ax, @data
    mov ds, ax

    ; Read initial head position
    lea dx, prompt_head
    mov ah, 09h
    int 21h
    call read_num
    mov initial_head, ax
    
    lea dx, newline
    mov ah, 09h
    int 21h

    ; Read number of requests (n)
    lea dx, prompt_n
    mov ah, 09h
    int 21h
    call read_num
    mov n, ax
    
    lea dx, newline
    mov ah, 09h
    int 21h

    ; Loop to read n requests
    mov cx, n
    lea si, requests
read_loop:
    push cx             ; Preserve loop counter
    
    lea dx, prompt_req
    mov ah, 09h
    int 21h
    
    call read_num
    mov [si], ax        ; Store track request in array
    add si, 2           ; Move to next word (16-bit)
    
    lea dx, newline
    mov ah, 09h
    int 21h
    
    pop cx              ; Restore loop counter
    loop read_loop

    ; --- FCFS Calculation ---
    mov cx, n
    lea si, requests
    mov bx, initial_head
    mov total_mov, 0    ; Initialize total movement to 0
    
fcfs_loop:
    push cx             ; Save outer loop counter
    
    mov ax, [si]        ; AX = current_request
    mov di, ax          ; Save current_request in DI for the next iteration
    
    ; Calculate |current_request - previous_position|
    sub ax, bx          ; AX = current_request - previous_position
    jns positive_diff   ; If positive (Sign Flag = 0), skip negation
    neg ax              ; If negative, make it positive (Two's complement)
    
positive_diff:
    ; AX now holds the seek time for this step
    add total_mov, ax   ; Accumulate total head movement
    
    ; --- Print step information ---
    push ax             ; Save the current seek time
    
    lea dx, msg_step
    mov ah, 09h
    int 21h
    
    mov ax, di          ; Load current track
    call print_num      ; Print track number
    
    lea dx, msg_step_mov
    mov ah, 09h
    int 21h
    
    pop ax              ; Restore seek time
    call print_num      ; Print seek time for this step
    ; ------------------------------
    
    mov bx, di          ; previous_position = current_request
    add si, 2           ; Move to next request in array
    pop cx              ; Restore outer loop counter
    loop fcfs_loop

    ; Print total head movement message
    lea dx, msg_total
    mov ah, 09h
    int 21h
    
    ; Print the accumulated total
    mov ax, total_mov
    call print_num
    
    ; --- Calculate and Print Average ---
    lea dx, msg_avg
    mov ah, 09h
    int 21h
    
    mov ax, total_mov
    mov dx, 0           ; Clear high word of dividend (DX:AX)
    mov bx, n
    cmp bx, 0
    je skip_avg         ; Prevent division by zero if n=0
    div bx              ; AX = total_mov / n
    
    call print_num      ; Print average
skip_avg:
    
    ; Print newline
    lea dx, newline
    mov ah, 09h
    int 21h

    ; Exit program
    mov ah, 4Ch
    int 21h
main endp

; Subroutine: Read a multi-digit number into AX
read_num proc
    push bx
    push cx
    mov bx, 0       ; Result accumulator
read_char:
    mov ah, 01h
    int 21h
    cmp al, 0Dh     ; Check for Enter (Carriage Return)
    je end_read
    cmp al, ' '     ; Check for Space
    je end_read
    
    sub al, '0'     ; Convert ASCII to integer
    mov cl, al
    mov ch, 0
    
    mov ax, bx
    mov dx, 10
    mul dx          ; Multiply accumulator by 10
    add ax, cx      ; Add new digit
    mov bx, ax
    jmp read_char
end_read:
    mov ax, bx      ; Store final result in AX
    pop cx
    pop bx
    ret
read_num endp

; Subroutine: Print a number in AX
print_num proc
    push ax
    push bx
    push cx
    push dx
    
    mov cx, 0       ; Digit counter
    mov bx, 10      ; Divisor
divide_loop:
    mov dx, 0
    div bx          ; AX = AX / 10, DX = AX % 10
    push dx         ; Push remainder (digit) onto stack
    inc cx          ; Increment digit count
    cmp ax, 0
    jne divide_loop
    
print_digits:
    pop dx          ; Get digit from stack
    add dl, '0'     ; Convert to ASCII
    mov ah, 02h
    int 21h
    loop print_digits
    
    pop dx
    pop cx
    pop bx
    pop ax
    ret
print_num endp

end main
```
