#!/bin/bash

read -p "Enter First Number : " num1
read -p "Enter Second Number : " num2
echo "Sum is $(( $num1 + $num2|bc -l ))"
echo "Difference is $(( $num1 - $num2|bc -l ))"
echo "Product is $(( $num1 * $num2|bc -l ))"