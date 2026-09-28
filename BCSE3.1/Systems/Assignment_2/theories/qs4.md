# Question 4: Sorting an Array of N Elements

## 1. What You Have to Do
You are tasked with writing a MASM assembly program that:
1. Prompts the user to enter the number of elements ($n$).
2. Reads $n$ integer elements from the user (handling both positive and **negative** numbers) and stores them in an array.
3. Sorts the array in ascending order using Bubble Sort.
4. Prints the sorted array back to the screen.

## 2. How to Do It (The Approach)
1. **User Input Handling**: Standard DOS interrupts only read one character at a time. We need a custom subroutine (`read_num`) to handle multiple digits. To support **negative numbers**, our subroutine checks if the first character is a minus sign (`-`). If it is, it sets a flag, continues reading the digits, and uses the `NEG` instruction at the end to make the final integer negative.
2. **Array Storage**: We allocate memory in the data segment (e.g., `array dw 100 dup(0)`). We use `dw` (Define Word) because 16-bit words naturally support signed integers from -32,768 to 32,767.
3. **Sorting Algorithm (Bubble Sort)**: 
   - An outer loop runs $n-1$ times.
   - An inner loop compares adjacent elements (`array[i]` and `array[i+1]`). Because we have negative numbers, we use the **Signed Jump** instruction `JLE` (Jump if Less or Equal) rather than unsigned jumps (`JBE`).
4. **Output Handling**: The `print_num` subroutine checks if the number in `AX` is negative using `CMP AX, 0`. If it's less than zero (`JL`), it prints a minus sign, negates the number using `NEG AX` to make it positive, and proceeds to divide by 10 to extract and print the digits.

## 3. The Theory Portion
### Reading and Parsing Integers
- DOS interrupt `INT 21h, AH=01h` reads a single character and echoes it.
- To read a multi-digit number, we read characters in a loop until a non-digit character (like a space or `Enter` `0Dh`) is detected.
- We convert the ASCII character to its numerical value by subtracting `30h` (or `'0'`).

### Signed vs. Unsigned Operations
In assembly, the processor doesn't inherently know if a binary sequence is a positive or negative number. It depends entirely on the instructions you use:
- **Unsigned Comparisons**: Use `JA` (Jump Above) and `JB` (Jump Below). If you compare `-5` and `2` using unsigned jumps, `-5` will be considered larger because its binary representation (`11111011`) is a huge positive number in unsigned format.
- **Signed Comparisons**: Use `JG` (Jump Greater) and `JL` (Jump Less). These instructions look at the **Sign Flag (SF)** and **Overflow Flag (OF)** to correctly evaluate negative values. This is why our sorting algorithm uses `JLE`.

### Number to String Conversion (Printing)
- To print a number, we repeatedly divide it by 10 using `DIV`. The remainder (`DX`) gives the last digit, and the quotient (`AX`) gives the remaining number.
- Because we extract digits from right to left (ones, tens, hundreds), we push these remainders onto the stack (LIFO - Last In, First Out).
- Once the quotient is zero, we pop the digits from the stack, add `30h` to convert them to ASCII, and print them using `INT 21h, AH=02h`.

## 4. Why This Approach?
Implementing Bubble Sort in assembly is an excellent exercise for understanding arrays, memory indexing (`[si]`), pointers, and nested loops at the hardware level. Adding support for negative numbers forces you to understand the difference between signed and unsigned jumps, which is a frequent source of bugs in low-level programming.

## 5. Code Implementation in MASM

```assembly
.model small
.stack 100h

.data
    prompt_n     db 'Enter the number of elements (n): $'
    prompt_elem  db 'Enter element: $'
    msg_sorted   db 10, 13, 'Sorted array: $'
    newline      db 10, 13, '$'
    
    n            dw ?
    array        dw 100 dup(0)

.code
main proc
    ; Initialize data segment
    mov ax, @data
    mov ds, ax

    ; Prompt for n
    lea dx, prompt_n
    mov ah, 09h
    int 21h

    call read_num
    mov n, ax

    ; Print newline
    lea dx, newline
    mov ah, 09h
    int 21h

    ; Loop to read n elements
    mov cx, n
    lea si, array
read_loop:
    push cx         ; Preserve loop counter
    
    lea dx, prompt_elem
    mov ah, 09h
    int 21h
    
    call read_num
    mov [si], ax    ; Store element in array
    add si, 2       ; Move to next word (2 bytes)
    
    lea dx, newline
    mov ah, 09h
    int 21h
    
    pop cx          ; Restore loop counter
    loop read_loop

    ; Bubble sort
    mov cx, n
    dec cx          ; outer loop counter = n - 1
    jz skip_sort    ; if n=1, no sort needed

outer_loop:
    mov bx, cx      ; inner loop counter
    lea si, array
inner_loop:
    mov ax, [si]
    cmp ax, [si+2]
    jle no_swap     ; if array[i] <= array[i+1] (SIGNED), do nothing
    
    ; Swap elements
    mov dx, [si+2]
    mov [si+2], ax
    mov [si], dx
    
no_swap:
    add si, 2       ; move to next element
    dec bx
    jnz inner_loop
    loop outer_loop

skip_sort:
    ; Print sorted array message
    lea dx, msg_sorted
    mov ah, 09h
    int 21h

    ; Loop to print n elements
    mov cx, n
    lea si, array
print_loop:
    mov ax, [si]
    call print_num  ; Print the number
    
    ; Print space
    mov dl, ' '
    mov ah, 02h
    int 21h
    
    add si, 2       ; Move to next word
    loop print_loop

    ; Print newline
    lea dx, newline
    mov ah, 09h
    int 21h

    ; Exit program
    mov ah, 4Ch
    int 21h
main endp

; Subroutine: Read a multi-digit number (handles negatives) into AX
read_num proc
    push bx
    push cx
    push dx
    push di
    
    mov bx, 0       ; Result accumulator
    mov di, 0       ; Flag for negative (0 = pos, 1 = neg)

read_first_char:
    mov ah, 01h
    int 21h
    cmp al, 0Dh     ; Check for Enter
    je end_read
    cmp al, ' '     ; Check for Space
    je end_read
    cmp al, '-'     ; Check for negative sign
    jne process_digit
    mov di, 1       ; Set negative flag
    jmp read_char   ; Go read the actual digits

read_char:
    mov ah, 01h
    int 21h
    cmp al, 0Dh
    je end_read
    cmp al, ' '
    je end_read

process_digit:
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
    cmp di, 1       ; Was it negative?
    jne return_read
    neg bx          ; If yes, two's complement negate the result

return_read:
    mov ax, bx      ; Store final result in AX
    pop di
    pop dx
    pop cx
    pop bx
    ret
read_num endp

; Subroutine: Print a number in AX (handles negatives)
print_num proc
    push ax
    push bx
    push cx
    push dx
    
    ; Check if negative
    cmp ax, 0
    jge print_positive
    
    ; If negative, print minus sign and negate AX
    push ax
    mov dl, '-'
    mov ah, 02h
    int 21h
    pop ax
    neg ax          ; Make it positive for division

print_positive:
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
