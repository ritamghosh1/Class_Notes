.model small
.stack 100h

.data
    prompt    db 10, 13, 'MYSHELL> $'
    err_msg   db 10, 13, 'Invalid command.$'
    err_file  db 10, 13, 'File error (does it exist?).$'
    msg_dir   db 10, 13, 'Directory Listing:', 10, 13, '  FILE1.TXT', 10, 13, '  NOTES.TXT', 10, 13, '  DATA.BIN$'
    msg_copy  db 10, 13, '1 file(s) copied.$'
    
    ; Input buffer for AH=0Ah (Max 60 chars, actual length, data)
    input_buf db 60, 0, 60 dup(0)
    
    ; Buffers to hold parsed filenames (ASCIIZ strings)
    file1     db 30 dup(0)
    file2     db 30 dup(0)
    
    ; File handles
    handle1   dw ?
    handle2   dw ?
    
    ; Buffer for reading file contents
    read_buf  db 128 dup(0)

.code
main proc
    ; Initialize data segment
    mov ax, @data
    mov ds, ax
    mov es, ax

shell_loop:
    ; 1. Print Prompt
    lea dx, prompt
    mov ah, 09h
    int 21h

    ; 2. Read user input
    lea dx, input_buf
    mov ah, 0Ah
    int 21h

    ; 3. Check input length
    mov cl, input_buf[1]    ; Fetch actual length read
    cmp cl, 0
    je shell_loop           ; If empty, just reprint prompt
    
    ; 4. Null-terminate the string (replace 0Dh with 00h)
    mov ch, 0
    lea si, input_buf[2]    ; Point to start of actual string
    add si, cx              ; Move to the end of the string
    mov byte ptr [si], 0    ; Place null terminator

    ; 5. Reset SI to start parsing
    lea si, input_buf[2]
    
skip_spaces:
    mov al, [si]
    cmp al, ' '
    jne parse_command
    inc si
    jmp skip_spaces

parse_command:
    ; --- Check for EXIT ---
    cmp byte ptr [si], 'E'
    jne not_exit
    cmp byte ptr [si+1], 'X'
    jne not_exit
    cmp byte ptr [si+2], 'I'
    jne not_exit
    cmp byte ptr [si+3], 'T'
    jne not_exit
    jmp do_exit
not_exit:

    ; --- Check for DIR ---
    cmp byte ptr [si], 'D'
    jne not_dir
    cmp byte ptr [si+1], 'I'
    jne not_dir
    cmp byte ptr [si+2], 'R'
    jne not_dir
    jmp do_dir
not_dir:

    ; --- Check for TYPE ---
    cmp byte ptr [si], 'T'
    jne not_type
    cmp byte ptr [si+1], 'Y'
    jne not_type
    cmp byte ptr [si+2], 'P'
    jne not_type
    cmp byte ptr [si+3], 'E'
    jne not_type
    add si, 4               ; Skip past the word "TYPE"
    jmp do_type
not_type:

    ; --- Check for COPY ---
    cmp byte ptr [si], 'C'
    jne not_copy
    cmp byte ptr [si+1], 'O'
    jne not_copy
    cmp byte ptr [si+2], 'P'
    jne not_copy
    cmp byte ptr [si+3], 'Y'
    jne not_copy
    add si, 4               ; Skip past the word "COPY"
    jmp do_copy
not_copy:

invalid_cmd:
    ; Command not recognized
    lea dx, err_msg
    mov ah, 09h
    int 21h
    jmp shell_loop

; =========================================
; Command Executions
; =========================================

do_exit:
    mov ah, 4Ch
    int 21h

do_dir:
    ; Simulate DIR by printing a fake list
    lea dx, msg_dir
    mov ah, 09h
    int 21h
    jmp shell_loop

do_type:
    ; Extract filename into file1
    call skip_spaces_sub
    lea di, file1
type_copy:
    mov al, [si]
    cmp al, ' '
    je type_end
    cmp al, 0
    je type_end
    mov [di], al
    inc si
    inc di
    jmp type_copy
type_end:
    mov byte ptr [di], 0    ; Null terminate file1

    ; Open file (AH=3Dh)
    lea dx, file1
    mov ah, 3Dh
    mov al, 0               ; Mode: 0 = Read Only
    int 21h
    jc file_error           ; If carry flag is set, error occurred
    mov handle1, ax         ; Save handle

type_read_loop:
    ; Read from file (AH=3Fh)
    mov ah, 3Fh
    mov bx, handle1
    lea dx, read_buf
    mov cx, 1               ; Read 1 byte at a time for easy printing
    int 21h
    jc file_error
    cmp ax, 0               ; Bytes read == 0 means EOF
    je type_close

    ; Print character
    mov dl, read_buf
    mov ah, 02h
    int 21h
    jmp type_read_loop

type_close:
    ; Close file (AH=3Eh)
    mov ah, 3Eh
    mov bx, handle1
    int 21h
    jmp shell_loop

do_copy:
    ; Extract source filename into file1
    call skip_spaces_sub
    lea di, file1
copy_src_copy:
    mov al, [si]
    cmp al, ' '
    je copy_src_end
    cmp al, 0
    je invalid_cmd          ; If end of string here, missing destination file!
    mov [di], al
    inc si
    inc di
    jmp copy_src_copy
copy_src_end:
    mov byte ptr [di], 0    ; Null terminate source file
    
    ; Extract destination filename into file2
    call skip_spaces_sub
    lea di, file2
copy_dest_copy:
    mov al, [si]
    cmp al, ' '
    je copy_dest_end
    cmp al, 0
    je copy_dest_end
    mov [di], al
    inc si
    inc di
    jmp copy_dest_copy
copy_dest_end:
    mov byte ptr [di], 0    ; Null terminate dest file

    ; 1. Open source file
    lea dx, file1
    mov ah, 3Dh
    mov al, 0               ; Read Only
    int 21h
    jc file_error
    mov handle1, ax

    ; 2. Create destination file
    lea dx, file2
    mov ah, 3Ch
    mov cx, 0               ; Normal file attribute
    int 21h
    jc file_error
    mov handle2, ax

copy_read_loop:
    ; 3. Read chunk from source
    mov ah, 3Fh
    mov bx, handle1
    lea dx, read_buf
    mov cx, 128             ; Read 128 bytes at a time
    int 21h
    jc file_error
    cmp ax, 0               ; 0 bytes read = EOF
    je copy_close

    ; 4. Write chunk to destination
    mov cx, ax              ; CX = number of bytes actually read
    mov ah, 40h
    mov bx, handle2
    lea dx, read_buf
    int 21h
    jc file_error
    jmp copy_read_loop

copy_close:
    ; 5. Close both handles
    mov ah, 3Eh
    mov bx, handle1
    int 21h
    
    mov ah, 3Eh
    mov bx, handle2
    int 21h

    ; Print success message
    lea dx, msg_copy
    mov ah, 09h
    int 21h
    jmp shell_loop

file_error:
    lea dx, err_file
    mov ah, 09h
    int 21h
    jmp shell_loop

main endp

; =========================================
; Subroutine: skip_spaces_sub
; Advances SI until a non-space character is found.
; =========================================
skip_spaces_sub proc
ss_loop:
    mov al, [si]
    cmp al, ' '
    jne ss_done
    inc si
    jmp ss_loop
ss_done:
    ret
skip_spaces_sub endp

end main
