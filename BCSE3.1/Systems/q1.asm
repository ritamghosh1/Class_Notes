.model small
.stack 100h

.data
    ; 0Dh, 0Ah represents Carriage Return and Line Feed (new line)
    name_msg db 'Name: Ritam', 0Dh, 0Ah, '$'
    title_msg db 'Program Title: Systems Program lab Assignment', 0Dh, 0Ah, '$'

.code
main proc
    ; Initialize the Data Segment
    mov ax, seg name_msg
    mov ds, ax

    ; Print the name string
    lea dx, name_msg
    mov ah, 09h
    int 21h

    ; Print the title string
    lea dx, title_msg
    mov ah, 09h
    int 21h

    ; Exit program gracefully
    mov ah, 4ch
    int 21h
main endp
end main