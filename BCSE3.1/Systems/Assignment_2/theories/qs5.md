# Question 5: Balanced Bracket Verification using a Stack

## 1. What You Have to Do
You are tasked with writing a MASM assembly program that verifies whether a string of brackets `()`, `{}`, and `[]` is balanced and properly nested. The program must:
1. Accept an expression (a string of brackets) from the user.
2. Simulate a **stack-based approach** to evaluate the brackets.
3. Push opening brackets `(`, `{`, `[` onto the stack.
4. Pop from the stack when a closing bracket `)`, `}`, `]` is encountered and verify it perfectly matches the popped opening bracket.
5. Print `Balanced` if all brackets match and the stack is completely empty at the end. Otherwise, print `Non-Balanced`.

## 2. How to Do It (The Approach)
1. **Simulating a Stack**: While x86 processors have a built-in hardware stack (using `PUSH` and `POP`), it strictly operates on 16-bit words. Because ASCII characters are 8-bit bytes, simulating our own stack using a byte array (e.g., `stack_arr db 100 dup(0)`) and a `top` pointer variable is much cleaner and avoids messy byte-to-word conversions.
2. **Reading Input**: We use DOS interrupt `INT 21h, AH=01h` to read characters one by one in a loop until the `Enter` key (`0Dh`) is pressed.
3. **Evaluation Logic**:
   - If the character is `(`, `{`, or `[`, we write it to `stack_arr[top]` and increment `top`.
   - If the character is `)`, `}`, or `]`, we must pop from the stack. If `top` is `0`, the stack is empty (meaning we received a closing bracket without an opening one), so we output `Non-Balanced`. Otherwise, we decrement `top`, read the character at `stack_arr[top]`, and compare it to the expected opening bracket. If they don't match, output `Non-Balanced`.
4. **Final Check**: After `Enter` is pressed, we must verify that `top` is exactly `0`. If `top > 0`, it means there are unmatched opening brackets left over on the stack, so we output `Non-Balanced`. If `top == 0`, we output `Balanced`.

## 3. The Theory Portion
### Stack Data Structure
A stack is a **LIFO (Last-In-First-Out)** data structure. It is the perfect theoretical concept for checking nested structures (like brackets in math, or HTML tags in web development) because the most recently opened bracket is always the first one that needs to be closed.

### Memory Addressing with the `BX` Register
To simulate the stack, we use **Base Register Addressing**. We load our `top` variable into the `BX` register, and then use `[bx]` as an index into our `stack_arr`. 
- **To Push**: We move the character into `stack_arr[bx]`, then increment `top`.
- **To Pop**: We decrement `top`, then read the character from `stack_arr[bx]`.

### Error Handling (Status Flags in Subroutines)
When popping from the stack, if the stack is already empty (a phenomenon called **Stack Underflow**), it is an immediate failure for bracket matching. In our `pop_char` subroutine, we use the `AH` register as a custom "status flag". It returns `AH = 1` if the pop was successful, and `AH = 0` if the stack was empty. This allows the main loop to safely check `AH` and jump to the `unbalanced` state without crashing.

## 4. Why This Approach?
Using a simulated stack array instead of the hardware `PUSH/POP` instructions clearly demonstrates how software stacks are constructed under the hood using raw memory arrays and pointers. This is a foundational concept in systems programming and data structures.

## 5. Code Implementation in MASM

```assembly
.model small
.stack 100h

.data
    prompt    db 'Enter bracket expression: $'
    msg_bal   db 10, 13, 'Balanced$', 0
    msg_unbal db 10, 13, 'Non-Balanced$', 0
    
    ; Simulated Stack
    stack_arr db 100 dup(0)
    top       dw 0

.code
main proc
    ; Initialize data segment
    mov ax, @data
    mov ds, ax

    ; Print prompt
    lea dx, prompt
    mov ah, 09h
    int 21h

read_loop:
    ; Read a single character from keyboard
    mov ah, 01h
    int 21h
    
    cmp al, 0Dh     ; Is it the Enter key (Carriage Return)?
    je end_input
    
    ; Check for opening brackets (Push)
    cmp al, '('
    je push_char
    cmp al, '{'
    je push_char
    cmp al, '['
    je push_char
    
    ; Check for closing brackets (Pop and Compare)
    cmp al, ')'
    je check_paren
    cmp al, '}'
    je check_brace
    cmp al, ']'
    je check_bracket
    
    ; Ignore any other characters (like spaces or letters)
    jmp read_loop

push_char:
    mov bx, top
    mov stack_arr[bx], al   ; Push character onto simulated stack
    inc top                 ; Increment stack pointer
    jmp read_loop

check_paren:
    call pop_char
    cmp ah, 0               ; Check status flag: was stack empty?
    je unbalanced           ; If empty, it's unbalanced
    cmp al, '('             ; Did we pop the matching opening bracket?
    jne unbalanced          ; If not, it's unbalanced
    jmp read_loop

check_brace:
    call pop_char
    cmp ah, 0
    je unbalanced
    cmp al, '{'
    jne unbalanced
    jmp read_loop

check_bracket:
    call pop_char
    cmp ah, 0
    je unbalanced
    cmp al, '['
    jne unbalanced
    jmp read_loop

end_input:
    ; The user finished typing. We must check if the stack is completely empty.
    cmp top, 0
    jne unbalanced          ; If top > 0, there are unclosed opening brackets left
    
    ; If empty, the expression is perfectly balanced
    lea dx, msg_bal
    mov ah, 09h
    int 21h
    jmp exit_prog

unbalanced:
    ; Output Non-Balanced message
    lea dx, msg_unbal
    mov ah, 09h
    int 21h

exit_prog:
    ; Terminate program
    mov ah, 4Ch
    int 21h
main endp

; ---------------------------------------------------------
; Subroutine: pop_char
; Pops a character from the simulated stack into AL.
; Returns AH = 1 on success.
; Returns AH = 0 on failure (stack underflow).
; ---------------------------------------------------------
pop_char proc
    cmp top, 0
    je pop_empty            ; Check for stack underflow
    
    dec top                 ; Decrement pointer
    mov bx, top
    mov al, stack_arr[bx]   ; Retrieve character
    mov ah, 1               ; Set success flag
    ret
    
pop_empty:
    mov ah, 0               ; Set failure flag
    ret
pop_char endp

end main
```
