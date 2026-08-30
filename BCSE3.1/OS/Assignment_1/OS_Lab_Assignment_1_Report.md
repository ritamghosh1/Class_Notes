# Operating System Laboratory — Assignment 1

> **Name:** `<!-- PUT YOUR NAME HERE -->`
> **Roll No.:** `<!-- PUT YOUR ROLL NUMBER HERE -->`
> **Section:** `<!-- PUT YOUR SECTION HERE -->`
> **Date:** `<!-- PUT THE DATE HERE -->`

---

## Table of Contents

1. [Question 1](#question-1)
2. [Question 4](#question-4)
3. [Question 5](#question-5)
4. [Question 7](#question-7)
5. [Question 8](#question-8)

---

## Question 1

### Problem Statement

> Write a shell script that reads command line arguments and prints the number of arguments. Given this sequence of words as command line arguments "To the OS Laboratory at Alpha Lab Welcome", the script should echo back the information that there are 8 arguments. Additionally it should echo back some of the arguments in the following order: "Welcome To the OS Laboratory at Alpha Lab"

### Source Code — `qs1.sh`

```bash
#!/bin/bash
echo "There are $# Arguments"
echo "$8 $1 $2 $3 $4 $5 $6 $7"
```

### Terminal Output

```
$ bash qs1.sh To the OS Laboratory at Alpha Lab Welcome
There are 8 Arguments
Welcome To the OS Laboratory at Alpha Lab
```

---

## Question 4

### Problem Statement

> Write a shell script that counts and prints the total number of files in a particular directory and in all of its sub-directories. Also (i) print total no. of files (not directories) in each subdirectory with the name of the subdirectory, (ii) print only those file names that have been created within the past week.

### Source Code — `qs4.sh`

```bash
#!/bin/bash
echo "Enter the Directory Path : "
read path

if [ -d "$path" ]
then
    fileCount=$(find "$path" -type f|wc -l)

    echo "Total Number of Files : $fileCount"
    find "$path" -type d | while read folder
    do
        count=$(find "$folder" -maxdepth 1 -type f|wc -l)
        echo "Number of Files in $folder : $count"
    done

    echo "Files modified within the Last week are : "
    find "$path" -type f -mtime -7
fi
```

### Terminal Output

```
$ bash qs4.sh
Enter the Directory Path : 
JavaFiles
Total Number of Files :        4
Number of Files in JavaFiles :        4
Files modified within the Last week are : 
```

---

## Question 5

### Problem Statement

> Write a shell script that takes 4 file names (Java program files) as command line arguments and prints the frequency of the occurrences of the following 3 strings "public", "class", "int" in each file. The output (in tabular format) should clearly denote the frequency of the occurrences of each string in each file.

### Source Code — `qs5.sh`

```bash
#!/bin/bash

printf "%-15s %-10s %-10s %-10s\n" "File" "public" "class" "int"
echo "-------------------------------------------------------"
for file in "$@"
do 
    publicCount=$(grep -o "public" "$file" | wc -l)
    classCount=$(grep -o "class" "$file" | wc -l)
    intCount=$(grep -o "int" "$file" | wc -l)  

    printf "%-15s %-10s %-10s %-10s\n" "$file" "$publicCount" "$classCount" "$intCount"
done
```

### Sample Java Files Used

**File1.java**

```java
public class File1 {
    public static void main(String[] args) {
        // This is a simple public class.
        System.out.println("Hello from File1!");
    }
}
```

**File2.java**

```java
public class File2 {
    public static void main(String[] args) {
        int myInteger = 20;
        System.out.println("This is File2.");
        System.out.println("The value of myInteger is: " + myInteger);
    }
}
```

**File3.java**

```java
public class File3 {
    public void display() {
        System.out.println("This is a public method inside the File3 class.");
    }
    // Another class in the same file.
    class AnotherClass {
    }
}
```

**File4.java**

```java
public class File4 {
    private int privateInt = 100;

    public int getPrivateInt() {
        return privateInt;
    }
}
```

### Terminal Output

```
$ bash qs5.sh JavaFiles/File1.java JavaFiles/File2.java JavaFiles/File3.java JavaFiles/File4.java
File            public     class      int       
-------------------------------------------------------
File1.java      3          2          1         
File2.java      2          1          3         
File3.java      3          4          1         
File4.java      2          1          2         
```

---

## Question 7

### Problem Statement

> Extend the shell script written in question (6) to perform the following task: User is asked to enter another word. (i) The first word (entered in question (6)) to be replaced by the second word, if a match occurs, (ii) Ignore replacing Partial matches, but show that (iii) partial matches do exist, and (iv) match exists, if case sensitivity is ignored.

### Source Code — `qs7.sh`

```bash
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

escaped_search=$(printf '%s' "$search_string" | sed 's/[][\\/.^$*+?{}()|]/\\&/g')
escaped_replacement=$(printf '%s' "$replacement_string" | sed 's/[\\/&]/\\&/g')

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

    sed -i '' -E "s/([[:>:]])$escaped_search([[:>:]])/$escaped_replacement/g" "$filename"
    
    echo "Success! Replacement complete."
else
    echo "------------------------------------------------------------------------------------"
    echo "No exact whole-word matches found to replace."
fi
```

### Sample Input File — `sample.txt` (before replacement)

```
The quick brown fox jumps over the lazy dog.
The fox is very quick and clever.
Foxes are known to be quick animals.
```

### Terminal Output

```
$ bash qs7.sh
Enter the FileName : sample.txt
Enter the String to Search For : quick
Enter the Replacement String : fast
------------------------------------------------------------------------------------
Found        3 exact match(es) for 'quick'.
Replacing exact matches with 'fast'...
Success! Replacement complete.
```

### File Content After Replacement — `sample.txt`

```
The fast brown fox jumps over the lazy dog.
The fox is very fast and clever.
Foxes are known to be fast animals.
```

---

## Question 8

### Problem Statement

> Write a script called birthday_match.sh that takes two birthdays of the form DD/MM/YYYY (e.g., 15/05/2000) and returns whether there is a match if the two people were born on the same day of the week (e.g., Friday).

### Source Code — `qs8.sh`

```bash
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
```

### Terminal Output — Case 1: Match

```
$ bash qs8.sh 15/05/2000 22/09/2003
Person 1 was born on a Monday.
Person 2 was born on a Monday.
----------------------------------------
Match! Both people were born on a Monday.
```

### Terminal Output — Case 2: No Match

```
$ bash qs8.sh 15/05/2000 16/05/2000
Person 1 was born on a Monday.
Person 2 was born on a Tuesday.
----------------------------------------
No match. They were born on different days of the week.
```

---

*End of Assignment Report*
