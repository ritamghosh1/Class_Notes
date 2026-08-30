.model small
.stack 100h

.data
    prompt db 'Enter an uppercase letter: $'
    output_msg db 0Dh, 0Ah, 'The lowercase letter is: $'

.code
main proc
    ; Initialize the Data Segment
    mov ax, @data
    mov ds, ax

    ; 1. Print the prompt asking for input
    lea dx, prompt
    mov ah, 09h
    int 21h

    ; 2. Read a single character from the keyboard
    mov ah, 01h
    int 21h
    mov bl, al       ; Save the input character into BL

    ; 3. Convert to lowercase by adding 20h (32)
    add bl, 20h

    ; 4. Print the output message formatting (including new line)
    lea dx, output_msg
    mov ah, 09h
    int 21h

    ; 5. Print the converted character
    mov dl, bl       ; Move the lowercase character to DL for printing
    mov ah, 02h      ; DOS function to print a single character
    int 21h

    ; Exit program gracefully
    mov ah, 4ch
    int 21h
main endp
end main