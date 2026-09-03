; =============================================================================
; Q6: Read two strings, reverse the first string (display only), and check if
;     there is any common substring between the ORIGINAL string and STR2.
; =============================================================================
; Assembler: MASM (8086) - EXE format
; Approach:
;   - Read two strings from the user (STR1 and STR2).
;   - Copy STR1 into REV_BUF, reverse REV_BUF for display.
;   - Use a nested loop on ORIGINAL STR1 vs STR2 to find a common substring.
;   - Once found, print the matching characters sequentially.
; =============================================================================

.MODEL SMALL
.STACK 100H

.DATA
    MSG_IN1    DB 'Enter String 1: $'
    MSG_IN2    DB 0DH, 0AH, 'Enter String 2: $'
    
    BUF1       DB 51, ?, 51 DUP('$')   ; Original string (kept intact)
    BUF2       DB 51, ?, 51 DUP('$')   ; Second string
    REV_BUF    DB 51 DUP('$')          ; Reversed copy of STR1 (for display)
    
    MSG_REV    DB 0DH, 0AH, 'Reversed String 1: $'
    MSG_FOUND  DB 0DH, 0AH, 'Result: Common substring found: $'
    MSG_NFOUND DB 0DH, 0AH, 'Result: NO common substring found.$'

.CODE
MAIN PROC
    MOV AX, @DATA
    MOV DS, AX
    MOV ES, AX

    ; --- Read STR1 ---
    LEA DX, MSG_IN1
    MOV AH, 09H
    INT 21H
    LEA DX, BUF1
    CALL READ_STRING

    ; --- Read STR2 ---
    LEA DX, MSG_IN2
    MOV AH, 09H
    INT 21H
    LEA DX, BUF2
    CALL READ_STRING

    ; --- Copy BUF1 into REV_BUF ---
    LEA SI, BUF1 + 2
    LEA DI, REV_BUF
COPY_LOOP:
    MOV AL, [SI]
    MOV [DI], AL
    CMP AL, '$'
    JE DONE_COPY
    INC SI
    INC DI
    JMP COPY_LOOP
DONE_COPY:

    ; --- Reverse REV_BUF (for display only) ---
    LEA SI, REV_BUF
    CALL STRREV

    ; --- Print Reversed STR1 ---
    LEA DX, MSG_REV
    MOV AH, 09H
    INT 21H
    LEA DX, REV_BUF
    MOV AH, 09H
    INT 21H

    ; --- Check for Common Substring on ORIGINAL STR1 vs STR2 ---
    LEA SI, BUF1 + 2       ; Outer loop pointer (ORIGINAL STR1)
OUTER_1:
    MOV AL, [SI]
    CMP AL, '$'            ; End of string 1?
    JE NOT_FOUND

    LEA DI, BUF2 + 2       ; Inner loop pointer (STR2)
OUTER_2:
    MOV BL, [DI]
    CMP BL, '$'            ; End of string 2?
    JE NEXT_OUTER_1

    CMP AL, BL             ; Compare character
    JE FOUND_MATCH         ; First matching character found!

    INC DI                 ; Move to next char in STR2
    JMP OUTER_2

NEXT_OUTER_1:
    INC SI                 ; Move to next char in original STR1
    JMP OUTER_1

FOUND_MATCH:
    ; Print the "Found" message
    LEA DX, MSG_FOUND
    MOV AH, 09H
    INT 21H

    ; Print the common substring sequentially until they differ
PRINT_MATCH_LOOP:
    MOV AL, [SI]           ; Char from original STR1
    MOV DL, [DI]           ; Char from STR2
    
    CMP AL, '$'            ; Reached end of STR1?
    JE EXIT_PROG
    CMP DL, '$'            ; Reached end of STR2?
    JE EXIT_PROG
    
    CMP AL, DL             ; Do they still match?
    JNE EXIT_PROG          ; If they differ, we are done printing

    ; Print the matching character
    MOV AH, 02H            ; DL already contains the matching character
    INT 21H

    INC SI                 ; Move to next char in STR1
    INC DI                 ; Move to next char in STR2
    JMP PRINT_MATCH_LOOP

NOT_FOUND:
    LEA DX, MSG_NFOUND
    MOV AH, 09H
    INT 21H

EXIT_PROG:
    ; Print newline for cleanliness
    MOV DL, 0DH
    MOV AH, 02H
    INT 21H
    MOV DL, 0AH
    MOV AH, 02H
    INT 21H

    MOV AH, 4CH
    INT 21H
MAIN ENDP

; =============================================================
; READ_STRING: Prompts DOS to read a string into buffer (DX)
; =============================================================
READ_STRING PROC
    MOV AH, 0AH
    INT 21H
    
    MOV BX, DX
    XOR CH, CH
    MOV CL, [BX+1]           
    ADD BX, 2                
    ADD BX, CX               
    MOV BYTE PTR [BX], '$'   
    RET
READ_STRING ENDP

; =============================================================
; STRREV: Reverse a '$'-terminated string in place
; =============================================================
STRREV PROC
    PUSH SI
    PUSH DI

    MOV DI, SI
FIND_END:
    MOV AL, [DI]
    CMP AL, '$'
    JE FOUND_END
    INC DI
    JMP FIND_END

FOUND_END:
    DEC DI                   
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

REVERSE_DONE:
    POP DI
    POP SI
    RET
STRREV ENDP

END MAIN
