#!/bin/bash

read -p "Enter the Word : " word
until [[ $word == "quit" ]]; do
    echo "Length : ${#word}"
    read -p "Enter word again : " word
done
echo "Exiting the Program"