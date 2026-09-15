#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ipc.h>
#include <sys/msg.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#define NUM_LISTENERS 3
#define NUM_BROADCASTS 5
#define MSG_SIZE 128

// Message buffer structure for System V message queues
struct msgbuf {
  long mtype; // message type: listener_id + 1 (must be > 0)
  char mtext[MSG_SIZE];
};

// ─────────────────────────────────────────────────
// Listener process: receives weather updates
// ─────────────────────────────────────────────────
void listener(int msgid, int listener_id) {
  struct msgbuf msg;
  long my_type = listener_id + 1; // mtype must be > 0

  printf("  [Listener %d] Started (PID: %d), listening on mtype=%ld\n",
         listener_id, getpid(), my_type);
  fflush(stdout);

  while (1) {
    // Block until a message with our type arrives
    if (msgrcv(msgid, &msg, MSG_SIZE, my_type, 0) == -1) {
      perror("  msgrcv");
      exit(1);
    }

    // Check for termination sentinel
    if (strcmp(msg.mtext, "END") == 0) {
      printf("  [Listener %d] Received END signal. Exiting.\n", listener_id);
      fflush(stdout);
      break;
    }

    printf("  [Listener %d] Received: \"%s\"\n", listener_id, msg.mtext);
    fflush(stdout);
  }

  exit(0);
}

// ─────────────────────────────────────────────────
// Broadcaster process: sends weather info to all
// ─────────────────────────────────────────────────
int main() {
  printf("========================================\n");
  printf("  3a: Weather Broadcast (Message Queue)\n");
  printf("========================================\n\n");

  // Create a unique message queue
  key_t key = ftok("/tmp", 'W');
  if (key == -1) {
    perror("ftok");
    return 1;
  }

  int msgid = msgget(key, IPC_CREAT | 0666);
  if (msgid == -1) {
    perror("msgget");
    return 1;
  }
  printf("  [Broadcaster] Message queue created (id=%d)\n\n", msgid);
  fflush(stdout); // flush before fork so children don't re-print header

  // Fork listener processes
  pid_t pids[NUM_LISTENERS];
  for (int i = 0; i < NUM_LISTENERS; i++) {
    pids[i] = fork();
    if (pids[i] < 0) {
      perror("fork");
      return 1;
    }
    if (pids[i] == 0) {
      listener(msgid, i);
      // listener() calls exit(), but just in case:
      exit(0);
    }
  }

  // Give listeners a moment to start
  usleep(100000);

  // Weather data to broadcast
  const char *weather[] = {"Sunny, 32C, Humidity 45%",
                           "Partly Cloudy, 28C, Wind 15km/h",
                           "Thunderstorm Warning, 24C",
                           "Clear Skies, 30C, UV Index High",
                           "Light Rain, 22C, Humidity 80%"};

  // Broadcast each weather update to all listeners
  struct msgbuf msg;
  for (int b = 0; b < NUM_BROADCASTS; b++) {
    printf("\n  [Broadcaster] Sending: \"%s\"\n", weather[b]);
    fflush(stdout);

    for (int i = 0; i < NUM_LISTENERS; i++) {
      msg.mtype = i + 1; // each listener has a unique type
      strncpy(msg.mtext, weather[b], MSG_SIZE - 1);
      msg.mtext[MSG_SIZE - 1] = '\0';

      if (msgsnd(msgid, &msg, strlen(msg.mtext) + 1, 0) == -1) {
        perror("  msgsnd");
        return 1;
      }
    }
    usleep(200000); // small delay between broadcasts
  }

  // Send termination sentinel to all listeners
  printf("\n  [Broadcaster] Sending END signal to all listeners.\n");
  fflush(stdout);
  for (int i = 0; i < NUM_LISTENERS; i++) {
    msg.mtype = i + 1;
    strncpy(msg.mtext, "END", MSG_SIZE);
    if (msgsnd(msgid, &msg, strlen(msg.mtext) + 1, 0) == -1) {
      perror("  msgsnd END");
    }
  }

  // Wait for all listeners to finish
  for (int i = 0; i < NUM_LISTENERS; i++) {
    waitpid(pids[i], NULL, 0);
  }

  // Cleanup: remove the message queue
  if (msgctl(msgid, IPC_RMID, NULL) == -1) {
    perror("msgctl IPC_RMID");
  } else {
    printf("\n  [Broadcaster] Message queue removed. Done.\n");
  }

  return 0;
}
