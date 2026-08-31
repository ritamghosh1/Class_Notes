#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

int main() {
  int pipe1[2], pipe2[2];
  if (pipe(pipe1) == -1 || pipe(pipe2) == -1) {
    perror("Pipe creation failed");
    return 1;
  }

  pid_t pid = fork();
  if (pid > 0) {
    // Process X (Parent)
    close(pipe1[0]); // X doesnt read from pipe1
    close(pipe2[1]); // X doesnt write to pipe2

    int x = 100;

    printf("Process X is writing %d\n", x);
    write(pipe1[1], &x, sizeof(x));

    int y_read;
    printf("Process X is waiting to read \n");
    read(pipe2[0], &y_read, sizeof(y_read));
    printf("Process X read %d\n", y_read);

    close(pipe1[1]);
    close(pipe2[0]);
  } else {
    // Process Y (Child)
    close(pipe1[1]); // Y doesnt write to pipe1
    close(pipe2[0]); // Y doesnt read from pipe2

    int y =

        printf("Process Y is writing %d\n", y);
    write(pipe2[1], &y, sizeof(y));

    int x_read;
    printf("Process Y is waiting to read \n");
    read(pipe1[0], &x_read, sizeof(x_read));
    printf("Process Y read %d\n", x_read);

    close(pipe1[0]);
    close(pipe2[1]);
  }
  return 0;
}