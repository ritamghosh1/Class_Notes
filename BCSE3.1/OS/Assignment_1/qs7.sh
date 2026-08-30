#!/bin/bash

echo -n "Enter the FileName : "
read filename

if [ ! -f "$filename" ]; then
    echo "Error: The file $filename does not exist."
    exit 1
fi

echo -n "Enter the String to Search For : "
read search_string
echo -n "Enter the Replacement String : "
read replacement_string

escaped_search=$(printf '%s' "$search_string" | sed 's/[][\/.^$*+?{}()|]/\\&/g')
escaped_replacement=$(printf '%s' "$replacement_string" | sed 's/[\/&]/\\&/g')

total_matches=$(grep -F -o "$search_string" "$filename" | wc -l)
exact_matches=$(grep -F -o -w "$search_string" "$filename" | wc -l)
case_in_matches=$(grep -F -o -i "$search_string" "$filename" | wc -l)

if [ "$total_matches" -gt "$exact_matches" ]; then
    echo "Partial matches DO exist (the string is hidden inside other words)."
fi

if [ "$case_in_matches" -gt "$total_matches" ]; then
    echo "Additional matches exist if case sensitivity is ignored!"
elif [ "$case_in_matches" -gt 0 ] && [ "$total_matches" -eq 0 ]; then
    echo "Matches DO exist if case sensitivity is ignored (no exact-case matches found)."
fi

if [ "$exact_matches" -gt 0 ]; then
    echo "------------------------------------------------------------------------------------"
    echo "Found $exact_matches exact match(es) for '$search_string'."
    echo "Replacing exact matches with '$replacement_string'..."

    sed -i '' -E "s/([[:<:]])$escaped_search([[:>:]])/$escaped_replacement/g" "$filename"
    
    echo "Success! Replacement complete."
else
    echo "------------------------------------------------------------------------------------"
    echo "No exact whole-word matches found to replace."
fi
