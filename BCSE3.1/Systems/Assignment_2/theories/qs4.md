# Question 4: Sorting an Array of N Elements

## 1. What You Have to Do
You are tasked with writing a MASM assembly program that:
1. Prompts the user to enter the number of elements ($n$).
2. Reads $n$ integer elements from the user and stores them in an array.
3. Sorts the array in ascending order (using a simple sorting algorithm like Bubble Sort).
4. Prints the sorted array back to the screen.

## 2. How to Do It (The Approach)
1. **User Input Handling**: Standard DOS interrupts only read one character at a time. We need a custom subroutine to read multiple numeric characters, convert them from ASCII to their actual integer values, and combine them into a single multi-digit integer (by multiplying the current total by 10 and adding the new digit).
2. **Array Storage**: We allocate memory in the data segment (e.g., `array dw 100 dup(0)`) to hold the integers. Since these are numbers (which can exceed 255), we use `dw` (Define Word) to reserve 16-bit slots for each element.
3. **Sorting Algorithm (Bubble Sort)**: 
   - An outer loop runs $n-1$ times.
   - An inner loop compares adjacent elements (`array[i]` and `array[i+1]`) and swaps them if they are out of order.
4. **Output Handling**: A computer only natively understands numerical values, not how to print them. We must convert the 16-bit integer back to a string of ASCII characters by repeatedly dividing by 10, pushing the remainders to the stack, and then popping them to print the digits in the correct order.

## 3. The Theory Portion
### Reading and Parsing Integers
- DOS interrupt `INT 21h, AH=01h` reads a single character and echoes it.
- To read a multi-digit number, we read characters in a loop until a non-digit character (like a space or `Enter` `0Dh`) is detected.
- We convert the ASCII character to its numerical value by subtracting `30h` (or `'0'`).

### Bubble Sort Algorithm in Assembly
- **Pointers**: We use `SI` (Source Index) to point to the current element in the array. Since our array uses words (16 bits / 2 bytes), we increment `SI` by 2 to move to the next element.
- **Swapping**: To swap two elements, we load one into a register (e.g., `AX`), load the other into another register (e.g., `DX`), and then write them back in reverse order.
- **Nested Loops**: The outer loop controls how many passes we make, and the inner loop performs the adjacent comparisons.

### Number to String Conversion (Printing)
- To print a number, we repeatedly divide it by 10 using `DIV`. The remainder (`DX`) gives the last digit, and the quotient (`AX`) gives the remaining number.
- Because we extract digits from right to left (ones, tens, hundreds), we push these remainders onto the stack (LIFO - Last In, First Out).
- Once the quotient is zero, we pop the digits from the stack, add `30h` to convert them to ASCII, and print them using `INT 21h, AH=02h`.

## 4. Why This Approach?
Implementing Bubble Sort in assembly is an excellent exercise for understanding arrays, memory indexing (`[si]`), pointers, and nested loops at the hardware level. Additionally, writing your own number-to-string and string-to-number converters reinforces the fact that hardware processes raw binary, and formatting it for human consumption requires explicit instruction.

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
    jle no_swap     ; if array[i] <= array[i+1], do nothing
    
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
