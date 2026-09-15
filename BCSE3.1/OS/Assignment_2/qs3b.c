#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#define MSG_SIZE 256
#define NUM_EXCHANGES 4

// ─────────────────────────────────────────────────
// 3b: Telephonic Conversation using Pipes
//
// Two unnamed pipes simulate a full-duplex phone call:
//   pipe_c2r: Caller  -> Receiver
//   pipe_r2c: Receiver -> Caller
//
// The caller and receiver alternate sending messages.
// ─────────────────────────────────────────────────

int main() {
  printf("========================================\n");
  printf("  3b: Telephonic Conversation (Pipe)\n");
  printf("========================================\n\n");
  fflush(stdout);

  int pipe_c2r[2]; // caller writes, receiver reads
  int pipe_r2c[2]; // receiver writes, caller reads

  if (pipe(pipe_c2r) == -1 || pipe(pipe_r2c) == -1) {
    perror("pipe");
    return 1;
  }

  // Scripted dialogue
  const char *caller_lines[] = {"Hello? Is this the Domino's Pizza?",
                                "I'd like to order a large pepperoni pizza.",
                                "Yes, with extra cheese please.",
                                "Great, thanks! Goodbye."};

  const char *receiver_lines[] = {
      "Yes, this is Domino's! How can I help you?",
      "Sure! Any toppings you'd like to add?",
      "Got it! Your order will be ready in 30 minutes.",
      "Thank you for calling! Goodbye."};

  pid_t pid = fork();
  if (pid < 0) {
    perror("fork");
    return 1;
  }

  char buf[MSG_SIZE];

  if (pid > 0) {
    // ── CALLER (Parent) ──
    close(pipe_c2r[0]); // caller doesn't read from c2r
    close(pipe_r2c[1]); // caller doesn't write to r2c

    for (int i = 0; i < NUM_EXCHANGES; i++) {
      // Caller speaks
      printf("  [Caller]   : %s\n", caller_lines[i]);
      fflush(stdout);
      write(pipe_c2r[1], caller_lines[i], strlen(caller_lines[i]) + 1);

      // Caller listens (blocks until receiver responds)
      read(pipe_r2c[0], buf, MSG_SIZE);
      printf("  [Caller]   hears: \"%s\"\n", buf);
      fflush(stdout);

      usleep(300000); // pause between exchanges
    }

    close(pipe_c2r[1]);
    close(pipe_r2c[0]);
    wait(NULL);

    printf("\n  --- Call ended ---\n");

  } else {
    // ── RECEIVER (Child) ──
    close(pipe_c2r[1]); // receiver doesn't write to c2r
    close(pipe_r2c[0]); // receiver doesn't read from r2c

    for (int i = 0; i < NUM_EXCHANGES; i++) {
      // Receiver listens (blocks until caller speaks)
      read(pipe_c2r[0], buf, MSG_SIZE);
      printf("  [Receiver] hears: \"%s\"\n", buf);
      fflush(stdout);

      usleep(200000); // thinking pause

      // Receiver responds
      printf("  [Receiver] : %s\n", receiver_lines[i]);
      fflush(stdout);
      write(pipe_r2c[1], receiver_lines[i], strlen(receiver_lines[i]) + 1);
    }

    close(pipe_c2r[0]);
    close(pipe_r2c[1]);
    exit(0);
  }

  return 0;
}
