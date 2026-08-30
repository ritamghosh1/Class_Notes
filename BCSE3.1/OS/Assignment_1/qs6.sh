#!/bin/bash

echo -n "Enter File Name : "
read filename

if [ ! -f "$filename" ]; then
    echo "Error: The file $filename does not exist."
    exit 1
fi

echo -n "Enter the String to Search for : "
read search_string

total_occurences=$(grep -o "$search_string" "$filename" | wc -l)

if [ "$total_occurences" -eq 0 ]; then 
    echo "The String $search_string was not found in the file $filename."
else
    echo "The String $search_string was found $total_occurences times in the file $filename."
    echo "------------------------------------------------------------------------------------"

    echo "Line by Line Matches"
    grep -o -n "$search_string" "$filename" | cut -d: -f1 | uniq -c | awk '{print "Line " $2 ": " $1 " occurrence(s)"}'
fi
