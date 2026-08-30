#!/bin/bash
echo "Enter the Directory Path : "
read path

if [ -d "$path" ]
then
    fileCount=$(find "$path" -type f|wc -l)
    dirCount=$(find "$path" -type d|wc -l)
    dirCount=$((dirCount - 1)) 

    echo "Total Number of Files : $fileCount"
    echo "Total Number of Directories : $dirCount"

    echo "Files are : "
    find "$path" -type f
    echo
    echo "Directories are : "
    find "$path" -type d
    echo

    echo "Total Size of Files modified in the past week : "
    find "$path" -type f -exec du -ch {} + |tail -1
fi

