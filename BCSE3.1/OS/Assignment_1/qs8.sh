#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "Usage: ./birthday_match.sh <DD/MM/YYYY> <DD/MM/YYYY>"
    echo "Example: ./birthday_match.sh 15/05/2000 22/09/2003"
    exit 1
fi

date1="$1"
date2="$2"

day1=$(/bin/date -j -f "%d/%m/%Y" "$date1" "+%A" 2>/dev/null)
day2=$(/bin/date -j -f "%d/%m/%Y" "$date2" "+%A" 2>/dev/null)

if [ -z "$day1" ] || [ -z "$day2" ]; then
    echo "Error: Invalid date format or date does not exist."
    echo "Please ensure you use the exact DD/MM/YYYY format."
    exit 1
fi

echo "Person 1 was born on a $day1."
echo "Person 2 was born on a $day2."
echo "----------------------------------------"

if [ "$day1" = "$day2" ]; then
    echo "Match! Both people were born on a $day1."
else
    echo "No match. They were born on different days of the week."
fi
