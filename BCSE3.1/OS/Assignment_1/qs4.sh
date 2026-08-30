#!/bin/bash
echo "Enter the Directory Path : "
read path

if [ -d "$path" ]
then
    fileCount=$(find "$path" -type f|wc -l)

    echo "Total Number of Files : $fileCount"
    find "$path" -type d | while read folder
    do
        count=$(find "$folder" -maxdepth 1 -type f|wc -l)
        echo "Number of Files in $folder : $count"
    done

    echo "Files modified within the Last week are : "
    find "$path" -type f -mtime -7
fi
