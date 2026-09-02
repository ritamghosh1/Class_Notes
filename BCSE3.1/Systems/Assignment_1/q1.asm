; =============================================================================
; Q1: Transfer a block of 10 data bytes from memory location 3000H to 4000H.
;     Before transfer, multiply each element by 5, then add 10.
; =============================================================================
; Assembler: MASM (8086)
; =============================================================================

.MODEL SMALL
.STACK 100H

.DATA
    ; Source block at offset 3000H (we simulate with an array)
    ORG 3000H
    SRC_BLOCK DB 01H, 02H, 03H, 04H, 05H, 06H, 07H, 08H, 09H, 0AH

    ; Destination block at offset 4000H
    ORG 4000H
    DST_BLOCK DB 10 DUP(0)

.CODE
MAIN PROC
    MOV AX, @DATA
    MOV DS, AX              ; Initialize data segment

    LEA SI, SRC_BLOCK       ; SI -> source block (3000H)
    LEA DI, DST_BLOCK       ; DI -> destination block (4000H)
    MOV CX, 0AH             ; Counter = 10 elements

TRANSFER:
    MOV AL, [SI]            ; Load byte from source
    
    ; Multiply by 5: AL = AL * 5
    MOV BL, 05H             ; Multiplier = 5
    MUL BL                  ; AX = AL * BL (result in AX, we use AL)
    
    ; Add 10
    ADD AL, 0AH             ; AL = AL + 10
    
    MOV [DI], AL            ; Store result to destination
    
    INC SI                  ; Move to next source byte
    INC DI                  ; Move to next destination byte
    LOOP TRANSFER           ; Decrement CX, loop if CX != 0

    ; Exit to DOS
    MOV AH, 4CH
    INT 21H

MAIN ENDP
END MAIN
