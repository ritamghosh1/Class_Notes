#!/bin/bash

for(( i=1;i<=50;i++ ));do
    num1="$i"%3
    num2="$i"%5
    if [[ "$num1" -eq 0 && "$num2" -eq 0 ]];then
        echo "$i "
    fi
done