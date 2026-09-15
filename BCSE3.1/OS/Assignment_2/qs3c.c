#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#define NUM_LISTENERS 3
#define NUM_BROADCASTS 4
#define MSG_SIZE 256

// FIFO paths — one per listener for broadcast, one per listener for replies
// broadcast:  /tmp/qs3_bcast_<i>   (broadcaster writes, listener i reads)
// reply:      /tmp/qs3_reply_<i>   (listener i writes, broadcaster reads)

void get_bcast_path(int id, char *buf) {
  sprintf(buf, "/tmp/qs3_bcast_%d", id);
}

void get_reply_path(int id, char *buf) {
  sprintf(buf, "/tmp/qs3_reply_%d", id);
}

// ─────────────────────────────────────────────────
// Listener process: reads broadcasts, sends replies
// ─────────────────────────────────────────────────
void listener(int id) {
  char bcast_path[64], reply_path[64];
  char buf[MSG_SIZE];

  get_bcast_path(id, bcast_path);
  get_reply_path(id, reply_path);

  printf("  [Listener %d] Started (PID: %d)\n", id, getpid());
  fflush(stdout);

  // Open broadcast FIFO for reading (blocks until broadcaster opens write end)
  int bcast_fd = open(bcast_path, O_RDONLY);
  if (bcast_fd == -1) {
    perror("  listener open bcast");
    exit(1);
  }

  // Open reply FIFO for writing
  int reply_fd = open(reply_path, O_WRONLY);
  if (reply_fd == -1) {
    perror("  listener open reply");
    exit(1);
  }

  while (1) {
    ssize_t n = read(bcast_fd, buf, MSG_SIZE);
    if (n <= 0)
      break; // EOF or error — broadcaster closed

    // Check for termination
    if (strcmp(buf, "END") == 0) {
      printf("  [Listener %d] Received END. Exiting.\n", id);
      fflush(stdout);

      // Send final ack
      char ack[MSG_SIZE];
      snprintf(ack, MSG_SIZE, "Listener %d signing off.", id);
      write(reply_fd, ack, strlen(ack) + 1);
      break;
    }

    printf("  [Listener %d] Received: \"%s\"\n", id, buf);
    fflush(stdout);

    // Send a reply back to the broadcaster
    char reply[MSG_SIZE];
    snprintf(reply, MSG_SIZE, "Listener %d: Acknowledged \"%s\"", id, buf);
    write(reply_fd, reply, strlen(reply) + 1);
  }

  close(bcast_fd);
  close(reply_fd);
  exit(0);
}

// ─────────────────────────────────────────────────
// Broadcaster: sends updates, collects replies
// ─────────────────────────────────────────────────
int main() {
  printf("========================================\n");
  printf("  3c: Broadcast + Replies (Named FIFO)\n");
  printf("========================================\n\n");
  fflush(stdout);

  char bcast_paths[NUM_LISTENERS][64];
  char reply_paths[NUM_LISTENERS][64];

  // Create all FIFOs
  for (int i = 0; i < NUM_LISTENERS; i++) {
    get_bcast_path(i, bcast_paths[i]);
    get_reply_path(i, reply_paths[i]);

    // Remove old FIFOs if they exist, then create fresh
    unlink(bcast_paths[i]);
    unlink(reply_paths[i]);

    if (mkfifo(bcast_paths[i], 0666) == -1) {
      perror("mkfifo bcast");
      return 1;
    }
    if (mkfifo(reply_paths[i], 0666) == -1) {
      perror("mkfifo reply");
      return 1;
    }
  }

  printf("  [Broadcaster] FIFOs created.\n\n");
  fflush(stdout);

  // Fork listener processes
  pid_t pids[NUM_LISTENERS];
  for (int i = 0; i < NUM_LISTENERS; i++) {
    pids[i] = fork();
    if (pids[i] < 0) {
      perror("fork");
      return 1;
    }
    if (pids[i] == 0) {
      listener(i);
      exit(0);
    }
  }

  // Broadcaster opens all FIFOs
  int bcast_fds[NUM_LISTENERS];
  int reply_fds[NUM_LISTENERS];

  for (int i = 0; i < NUM_LISTENERS; i++) {
    bcast_fds[i] = open(bcast_paths[i], O_WRONLY);
    if (bcast_fds[i] == -1) {
      perror("broadcaster open bcast");
      return 1;
    }
  }
  for (int i = 0; i < NUM_LISTENERS; i++) {
    reply_fds[i] = open(reply_paths[i], O_RDONLY);
    if (reply_fds[i] == -1) {
      perror("broadcaster open reply");
      return 1;
    }
  }

  // Weather data
  const char *updates[] = {"Heatwave alert: 42C expected tomorrow",
                           "Rain forecast for evening, carry umbrellas",
                           "Air quality index: Moderate (AQI 120)",
                           "Weekend outlook: Pleasant, 26C"};

  char buf[MSG_SIZE];

  // Broadcast loop
  for (int b = 0; b < NUM_BROADCASTS; b++) {
    printf("\n  [Broadcaster] Sending: \"%s\"\n", updates[b]);
    fflush(stdout);

    // Write to each listener's FIFO
    for (int i = 0; i < NUM_LISTENERS; i++) {
      write(bcast_fds[i], updates[b], strlen(updates[b]) + 1);
    }

    usleep(100000); // give listeners time to respond

    // Read replies from each listener
    for (int i = 0; i < NUM_LISTENERS; i++) {
      ssize_t n = read(reply_fds[i], buf, MSG_SIZE);
      if (n > 0) {
        printf("  [Broadcaster] Reply: \"%s\"\n", buf);
        fflush(stdout);
      }
    }

    usleep(200000); // pause between broadcasts
  }

  // Send END to all listeners
  printf("\n  [Broadcaster] Sending END to all listeners.\n");
  fflush(stdout);
  for (int i = 0; i < NUM_LISTENERS; i++) {
    write(bcast_fds[i], "END", 4);
  }

  // Read final acks
  usleep(100000);
  for (int i = 0; i < NUM_LISTENERS; i++) {
    ssize_t n = read(reply_fds[i], buf, MSG_SIZE);
    if (n > 0) {
      printf("  [Broadcaster] Final: \"%s\"\n", buf);
      fflush(stdout);
    }
  }

  // Close FIFOs
  for (int i = 0; i < NUM_LISTENERS; i++) {
    close(bcast_fds[i]);
    close(reply_fds[i]);
  }

  // Wait for children
  for (int i = 0; i < NUM_LISTENERS; i++) {
    waitpid(pids[i], NULL, 0);
  }

  // Cleanup FIFOs
  for (int i = 0; i < NUM_LISTENERS; i++) {
    unlink(bcast_paths[i]);
    unlink(reply_paths[i]);
  }

  printf("\n  [Broadcaster] FIFOs cleaned up. Done.\n");
  return 0;
}
