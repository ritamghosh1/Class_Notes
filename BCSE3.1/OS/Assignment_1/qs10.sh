#!/bin/bash

TRASH_DIR="$HOME/my-deleted-files"

mkdir -p "$TRASH_DIR"

if [ "$#" -eq 0 ]; then
    echo "Usage: ./safe_rm.sh <filename1> <filename2> ..."
    echo "       ./safe_rm.sh -cl (to clear the trash)"
    exit 1
fi

if [ "$1" = "-cl" ]; then
    echo -n "Are you sure you want to permanently delete all files in the trash? (y/n): "
    read confirmation
    if [ "$confirmation" = "y" ] || [ "$confirmation" = "Y" ]; then
        rm -rf "$TRASH_DIR"/*
        echo "Trash directory cleared."
    else
        echo "Operation aborted. Files are safe."
    fi
    exit 0
fi

for file in "$@"; do
    
    if [ ! -e "$file" ]; then
        echo "Error: Cannot remove '$file'. No such file or directory."
        continue
    fi
    
    base_name=$(basename "$file")
    target="$TRASH_DIR/$base_name"
    
    if [ -e "$target" ] || [ -e "${target}.0" ]; then
        
        if [ -e "$target" ]; then
            mv "$target" "${target}.0"
        fi

        version=1
        while [ -e "${target}.${version}" ]; do
            version=$((version + 1))
        done

        mv "$file" "${target}.${version}"
        echo "Moved '$file' to trash as '${base_name}.${version}'"
        
    else
        mv "$file" "$target"
        echo "Moved '$file' to trash as '$base_name'"
    fi

done