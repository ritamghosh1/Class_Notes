#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define ITERATIONS 10

int main() {
  // 1. Create pipes BEFORE forking
  int pipe_xy[2]; // Pipe for X to signal Y
  int pipe_yx[2]; // Pipe for Y to signal X

  if (pipe(pipe_xy) == -1 || pipe(pipe_yx) == -1) {
    perror("Pipe creation failed");
    return 1;
  }

  pid_t pid = fork();
  if (pid < 0) {
    perror("Fork failed");
    exit(1);
  }

  // Seed random number generator uniquely for each process
  srand(time(NULL) ^ getpid());
  int token = 1; // A dummy value to pass through the pipe

  if (pid > 0) {
    // --- PROCESS X (Parent) ---
    close(pipe_xy[0]); // X doesn't read from xy
    close(pipe_yx[1]); // X doesn't write to yx

    for (int i = 1; i <= ITERATIONS; i++) {
      // Do the work
      printf("Process X - Iteration %d\n", i);
      fflush(stdout);
      usleep(rand() % 100000);

      // Signal Y that X is done with this iteration
      write(pipe_xy[1], &token, sizeof(token));

      // Wait for Y to finish its iteration before doing the next one
      // (Unless it's the very last iteration, then we don't need to wait)
      if (i < ITERATIONS) {
        read(pipe_yx[0], &token, sizeof(token));
      }
    }

    close(pipe_xy[1]);
    close(pipe_yx[0]);
    wait(NULL); // Wait for child to finish
    printf("Both processes finished.\n");

  } else {
    // --- PROCESS Y (Child) ---
    close(pipe_xy[1]); // Y doesn't write to xy
    close(pipe_yx[0]); // Y doesn't read from yx

    for (int i = 1; i <= ITERATIONS; i++) {
      // Wait for X to finish its iteration first
      read(pipe_xy[0], &token, sizeof(token));

      // Do the work
      printf("Process Y - Iteration %d\n", i);
      fflush(stdout);
      usleep(rand() % 100000);

      // Signal X that Y is done
      if (i < ITERATIONS) {
        write(pipe_yx[1], &token, sizeof(token));
      }
    }

    close(pipe_xy[0]);
    close(pipe_yx[1]);
    exit(0);
  }

  return 0;
}
