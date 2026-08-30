#!/bin/bash
while true
    do
        echo "Enter the first Number: "
        read a
        echo "Enter the second Number: "
        read b
        echo
        if [[ $a =~ ^-?[0-9]+([.]?[0-9]+)?$ && $b =~ ^-?[0-9]+([.][0-9]+)?$ ]]
        then
            echo "The sum of $a and $b is : $(echo "$a + $b" | bc)"
            echo "The difference of $a and $b is : $(echo "$a - $b" | bc)"
            echo "The product of $a and $b is : $(echo "$a * $b" | bc)"
            if (( $(echo "$b == 0" | bc -l) ));
            then
                echo "Division with 0 is not Possible"
            else
                echo "The quotient of $a and $b is : $(echo "scale=4; $a / $b" | bc)"
                echo "The remainder of $a and $b is : $(echo "$a % $b" | bc)"
            fi
        else 
            echo "Arithmetic Operation is not possible"
        fi
        echo
        echo "Reverse Order"
        echo "$b $a"
        echo "To Continue enter y or Y, else enter anything : "
        read choice
        if [[ "$choice" != "y" && "$choice" != "Y" ]]
        then break
        fi
    done

