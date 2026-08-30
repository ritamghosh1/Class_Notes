#!/bin/bash

printf "%-15s %-10s %-10s %-10s\n" "File" "public" "class" "int"
echo "-------------------------------------------------------"
for file in "$@"
do 
    publicCount=$(grep -o "public" "$file" | wc -l)
    classCount=$(grep -o "class" "$file" | wc -l)
    intCount=$(grep -o "int" "$file" | wc -l)  

    printf "%-15s %-10s %-10s %-10s\n" "$file" "$publicCount" "$classCount" "$intCount"
done
