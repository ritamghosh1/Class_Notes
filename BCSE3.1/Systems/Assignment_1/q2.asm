; =============================================================================
; Q2: Store an array of 20 numbers in zig-zag (alternating less-than and
;     greater-than) order in memory location 4000H.
;     Zig-zag: a[0] < a[1] > a[2] < a[3] > a[4] ...
; =============================================================================
; Assembler: MASM (8086)
; Approach: Bubble-sort style single pass with conditional swaps.
;   - At even indices (0, 2, 4...): ensure a[i] < a[i+1], else swap
;   - At odd indices (1, 3, 5...):  ensure a[i] > a[i+1], else swap
; =============================================================================

.MODEL SMALL
.STACK 100H

.DATA
    ; Unsorted source array of 20 bytes
    ARR DB 15, 03, 22, 07, 19, 01, 30, 12, 25, 08
        DB 17, 04, 28, 06, 21, 09, 14, 27, 02, 11
    COUNT EQU 20

    ; Destination at offset 4000H
    ORG 4000H
    RESULT DB 20 DUP(0)

.CODE
MAIN PROC
    MOV AX, @DATA
    MOV DS, AX

    ; --- Step 1: Copy array to destination at 4000H ---
    LEA SI, ARR
    LEA DI, RESULT
    MOV CX, COUNT
COPY_LOOP:
    MOV AL, [SI]
    MOV [DI], AL
    INC SI
    INC DI
    LOOP COPY_LOOP

    ; --- Step 2: Zig-zag sort in-place at RESULT ---
    LEA SI, RESULT
    MOV CX, COUNT - 1       ; 19 pairs to check (i=0 to 18)
    XOR BX, BX              ; BX = index counter (0 = even position)

ZIGZAG_LOOP:
    MOV AL, [SI]             ; a[i]
    MOV AH, [SI + 1]        ; a[i+1]

    TEST BX, 01H            ; Check if index is even or odd
    JNZ ODD_INDEX            ; If odd index, jump

EVEN_INDEX:
    ; Even index: need a[i] < a[i+1]
    CMP AL, AH
    JBE NO_SWAP              ; Already a[i] <= a[i+1], skip
    JMP DO_SWAP

ODD_INDEX:
    ; Odd index: need a[i] > a[i+1]
    CMP AL, AH
    JAE NO_SWAP              ; Already a[i] >= a[i+1], skip

DO_SWAP:
    MOV [SI], AH             ; Swap a[i] and a[i+1]
    MOV [SI + 1], AL

NO_SWAP:
    INC SI                   ; Move to next element
    INC BX                   ; Increment index counter
    LOOP ZIGZAG_LOOP

    ; Exit to DOS
    MOV AH, 4CH
    INT 21H

MAIN ENDP
END MAIN
