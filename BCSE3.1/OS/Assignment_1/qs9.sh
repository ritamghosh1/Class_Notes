#!/bin/bash

echo -n "Enter an integer to find its factorial: "
read n

if ! [[ "$n" =~ ^[0-9]+$ ]]; then
    echo "Error: Please enter a valid non-negative integer (e.g., 5)."
    exit 1
fi

echo "Calculating $n! ..."
echo "--------------------------------------------------------"

time {
    factorial=1
    
    for (( i=1; i<=n; i++ )); do
        factorial=$(echo "$factorial * $i" | bc)
    done
    
    echo "Result: $factorial"
    echo "--------------------------------------------------------"
}
