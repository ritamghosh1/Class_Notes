#!/bin/bash

if [[ $# -lt 1 ]];then
    echo "Enter Number : <num>"
    exit 1
fi

num=$1
rem=$(( $num % 2 ))
if [[ $rem -eq 0 ]];then
    echo "$num is Even"
else
    echo "$num is Odd"
fi