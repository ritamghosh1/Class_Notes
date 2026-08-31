#!/bin/bash
if [[ $# -lt 2 ]];then
    echo "Missing CL args : <name> <age>"
    exit 1
fi
name=$1
age=$2
echo "$name is $age years old"