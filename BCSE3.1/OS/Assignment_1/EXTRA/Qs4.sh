#!/bin/bash

read -p "Enter the Filename : " filename

if [[ -f "$filename" ]];then
    echo "This is a File"
elif [[ -d "$filename" ]];then
    echo "This is a Directory"
else
    echo "This is neither a File nor a Directory"
fi