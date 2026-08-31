#!/bin/bash

if [[ "$#" -lt 1 ]];then
    echo "Enter the Sentence"
    exit 1
fi

i=1
for word in $1;do
    echo "$i : $word"
    i=$((i + 1))
done