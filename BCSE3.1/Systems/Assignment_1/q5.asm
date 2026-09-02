; =============================================================================
; Q5: Library of String Operations
;     a. STRLEN  - Return length of a '$'-terminated string
;     b. STRCMP   - Compare two strings (returns 0 if equal, 1 if not)
;     c. STRREV  - Reverse a string in place
; =============================================================================
; Assembler: MASM (8086)
; =============================================================================

.MODEL SMALL
.STACK 100H

.DATA
    ; Test strings
    STR1    DB 'Hello, World!', '$'
    STR2    DB 'Hello, World!', '$'
    STR3    DB 'Different', '$'
    STR_REV DB 'ABCDEF', '$'

    ; Output messages
    MSG_LEN    DB 0DH, 0AH, '--- STRLEN ---', 0DH, 0AH, '$'
    MSG_LEN_R  DB 0DH, 0AH, 'Length of STR1: $'

    MSG_CMP    DB 0DH, 0AH, '--- STRCMP ---', 0DH, 0AH, '$'
    MSG_EQ     DB 0DH, 0AH, 'STR1 and STR2 are EQUAL$'
    MSG_NEQ    DB 0DH, 0AH, 'STR1 and STR3 are NOT EQUAL$'

    MSG_REV    DB 0DH, 0AH, '--- STRREV ---', 0DH, 0AH, '$'
    MSG_BEF    DB 0DH, 0AH, 'Before reverse: $'
    MSG_AFT    DB 0DH, 0AH, 'After reverse:  $'

    NEWLINE    DB 0DH, 0AH, '$'

.CODE
MAIN PROC
    MOV AX, @DATA
    MOV DS, AX

    ; =============================================
    ; Demo STRLEN
    ; =============================================
    LEA DX, MSG_LEN
    MOV AH, 09H
    INT 21H

    LEA DX, MSG_LEN_R
    MOV AH, 09H
    INT 21H

    LEA SI, STR1
    CALL STRLEN              ; Result in CX
    ; Display length (CX contains length)
    MOV AX, CX
    CALL PRINT_NUMBER

    ; =============================================
    ; Demo STRCMP (STR1 vs STR2 - should be equal)
    ; =============================================
    LEA DX, MSG_CMP
    MOV AH, 09H
    INT 21H

    LEA SI, STR1
    LEA DI, STR2
    CALL STRCMP               ; Result: AX=0 if equal, AX=1 if not

    CMP AX, 0
    JNE SKIP_EQ
    LEA DX, MSG_EQ
    MOV AH, 09H
    INT 21H
SKIP_EQ:

    ; Demo STRCMP (STR1 vs STR3 - should be different)
    LEA SI, STR1
    LEA DI, STR3
    CALL STRCMP

    CMP AX, 0
    JE SKIP_NEQ
    LEA DX, MSG_NEQ
    MOV AH, 09H
    INT 21H
SKIP_NEQ:

    ; =============================================
    ; Demo STRREV
    ; =============================================
    LEA DX, MSG_REV
    MOV AH, 09H
    INT 21H

    ; Print before
    LEA DX, MSG_BEF
    MOV AH, 09H
    INT 21H
    LEA DX, STR_REV
    MOV AH, 09H
    INT 21H

    ; Reverse
    LEA SI, STR_REV
    CALL STRREV

    ; Print after
    LEA DX, MSG_AFT
    MOV AH, 09H
    INT 21H
    LEA DX, STR_REV
    MOV AH, 09H
    INT 21H

    ; Exit
    MOV AH, 4CH
    INT 21H
MAIN ENDP

; =============================================================
; STRLEN: Returns the length of a '$'-terminated string
; Input:  SI -> pointer to string
; Output: CX = length of string (excluding '$')
; =============================================================
STRLEN PROC
    PUSH SI                  ; Save registers
    XOR CX, CX              ; CX = 0 (length counter)

STRLEN_LOOP:
    MOV AL, [SI]
    CMP AL, '$'              ; Check for terminator
    JE STRLEN_DONE
    INC CX                   ; Increment length
    INC SI                   ; Next character
    JMP STRLEN_LOOP

STRLEN_DONE:
    POP SI
    RET
STRLEN ENDP

; =============================================================
; STRCMP: Compare two '$'-terminated strings
; Input:  SI -> string 1, DI -> string 2
; Output: AX = 0 if equal, AX = 1 if not equal
; =============================================================
STRCMP PROC
    PUSH SI
    PUSH DI

STRCMP_LOOP:
    MOV AL, [SI]
    MOV BL, [DI]
    CMP AL, BL
    JNE STRCMP_NOT_EQUAL      ; Characters differ

    CMP AL, '$'              ; Both reached terminator?
    JE STRCMP_EQUAL           ; Yes -> strings are equal

    INC SI
    INC DI
    JMP STRCMP_LOOP

STRCMP_EQUAL:
    XOR AX, AX              ; AX = 0 (equal)
    JMP STRCMP_DONE

STRCMP_NOT_EQUAL:
    MOV AX, 1               ; AX = 1 (not equal)

STRCMP_DONE:
    POP DI
    POP SI
    RET
STRCMP ENDP

; =============================================================
; STRREV: Reverse a '$'-terminated string in place
; Input:  SI -> pointer to string
; Uses two-pointer technique: front (SI) and back (DI)
; =============================================================
STRREV PROC
    PUSH SI
    PUSH DI

    ; First, find the end of the string (DI -> last char before '$')
    MOV DI, SI
FIND_END:
    MOV AL, [DI]
    CMP AL, '$'
    JE FOUND_END
    INC DI
    JMP FIND_END

FOUND_END:
    DEC DI                   ; DI now points to last character

    ; Now SI -> first char, DI -> last char
    ; Swap characters moving inward until SI >= DI
REVERSE_LOOP:
    CMP SI, DI
    JAE REVERSE_DONE         ; Pointers met or crossed

    MOV AL, [SI]             ; Swap [SI] and [DI]
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

; =============================================================
; PRINT_NUMBER: Display a number in AX as decimal
; Input:  AX = number to display
; =============================================================
PRINT_NUMBER PROC
    PUSH AX
    PUSH BX
    PUSH CX
    PUSH DX

    XOR CX, CX              ; Digit counter
    MOV BX, 10

PN_PUSH:
    XOR DX, DX
    DIV BX                   ; AX = quotient, DX = remainder
    PUSH DX
    INC CX
    CMP AX, 0
    JNE PN_PUSH

PN_PRINT:
    POP DX
    ADD DL, 30H
    MOV AH, 02H
    INT 21H
    LOOP PN_PRINT

    POP DX
    POP CX
    POP BX
    POP AX
    RET
PRINT_NUMBER ENDP

END MAIN
