#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>

#define ITERATIONS 10

void run_child(const char* name) {
    // Seed the random number generator uniquely for each child using its PID
    srand(time(NULL) ^ getpid());
    
    for (int i = 1; i <= ITERATIONS; i++) {
        printf("Process %s - Iteration %d\n", name, i);
        fflush(stdout); // Ensure immediate printing
        
        // Sleep for a random amount of time between 0 and 99999 microseconds (up to 0.1s)
        usleep(rand() % 100000);
    }
    exit(0);
}

int main() {
    pid_t pid_x = fork();
    if (pid_x < 0) {
        perror("Fork failed for X");
        exit(1);
    } else if (pid_x == 0) {
        run_child("X");
    }

    pid_t pid_y = fork();
    if (pid_y < 0) {
        perror("Fork failed for Y");
        exit(1);
    } else if (pid_y == 0) {
        run_child("Y");
    }

    // Parent waits for both children to finish
    wait(NULL);
    wait(NULL);
    
    printf("Both processes finished.\n");
    return 0;
}