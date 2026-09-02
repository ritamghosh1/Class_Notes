; =============================================================================
; Q3: Convert a hexadecimal number into its equivalent ASCII string.
;     Example: 4Bh -> displays "4B"
; =============================================================================
; Assembler: MASM (8086)
; Approach: Extract each nibble (4 bits) of the hex byte, convert to ASCII
;           character ('0'-'9' or 'A'-'F'), and display using DOS INT 21H.
; =============================================================================

.MODEL SMALL
.STACK 100H

.DATA
    HEX_NUM DB 4BH          ; Input hex number to convert
    MSG1 DB 'Hex number: $'
    MSG2 DB 0DH, 0AH, 'ASCII equivalent: $'
    RESULT DB 3 DUP('$')    ; Store 2 ASCII chars + '$' terminator

.CODE
MAIN PROC
    MOV AX, @DATA
    MOV DS, AX

    ; Display label
    LEA DX, MSG1
    MOV AH, 09H
    INT 21H

    ; Load the hex number
    MOV AL, HEX_NUM

    ; --- Convert upper nibble (high 4 bits) ---
    MOV BL, AL              ; Save original in BL
    SHR AL, 4               ; Shift right by 4 to get upper nibble (use CL for 8086)
    ; Note: For strict 8086, use: MOV CL, 4 / SHR AL, CL
    CALL NIBBLE_TO_ASCII
    MOV RESULT[0], AL       ; Store first ASCII char

    ; --- Convert lower nibble (low 4 bits) ---
    MOV AL, BL              ; Restore original
    AND AL, 0FH             ; Mask to get lower nibble
    CALL NIBBLE_TO_ASCII
    MOV RESULT[1], AL       ; Store second ASCII char

    ; Display the result
    LEA DX, MSG2
    MOV AH, 09H
    INT 21H

    LEA DX, RESULT
    MOV AH, 09H
    INT 21H

    ; Exit to DOS
    MOV AH, 4CH
    INT 21H
MAIN ENDP

; -------------------------------------------------
; NIBBLE_TO_ASCII: Convert a nibble (0-F) in AL to
;                  its ASCII character ('0'-'9','A'-'F')
; Input:  AL = 0x00 to 0x0F
; Output: AL = ASCII character
; -------------------------------------------------
NIBBLE_TO_ASCII PROC
    CMP AL, 09H
    JBE IS_DIGIT             ; If AL <= 9, it's a digit
    ADD AL, 37H              ; 0AH + 37H = 41H = 'A'
    RET
IS_DIGIT:
    ADD AL, 30H              ; 00H + 30H = 30H = '0'
    RET
NIBBLE_TO_ASCII ENDP

END MAIN
