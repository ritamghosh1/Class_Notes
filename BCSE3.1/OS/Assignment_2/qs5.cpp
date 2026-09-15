#include <cstdlib>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

using namespace std;

// Parses numbers from the formatted input file
vector<int> parse_file(const string &filename) {
  ifstream file(filename);
  vector<int> nums;
  if (!file) {
    cerr << "Error opening file: " << filename << endl;
    exit(1);
  }
  char c;
  int current_num = -1;
  while (file.get(c)) {
    if (isdigit(c)) {
      if (current_num == -1)
        current_num = c - '0';
      else
        current_num = current_num * 10 + (c - '0');
    } else {
      if (current_num != -1) {
        nums.push_back(current_num);
        current_num = -1;
      }
    }
  }
  if (current_num != -1)
    nums.push_back(current_num);
  return nums;
}

// Banker's Algorithm safety check
bool isSafe(int n, int m, const vector<int> &available,
            const vector<vector<int>> &max_mat,
            const vector<vector<int>> &alloc_mat, vector<int> &safe_seq) {
  vector<int> work = available;
  vector<bool> finish(n, false);
  safe_seq.clear();

  int count = 0;
  while (count < n) {
    bool found = false;
    for (int p = 0; p < n; p++) {
      if (!finish[p]) {
        bool can_alloc = true;
        for (int j = 0; j < m; j++) {
          // Need[p][j] = max_mat[p][j] - alloc_mat[p][j]
          if (max_mat[p][j] - alloc_mat[p][j] > work[j]) {
            can_alloc = false;
            break;
          }
        }

        if (can_alloc) {
          for (int j = 0; j < m; j++)
            work[j] += alloc_mat[p][j];
          safe_seq.push_back(p);
          finish[p] = true;
          found = true;
          count++;
        }
      }
    }
    if (!found) {
      return false;
    }
  }
  return true;
}

void printState(int n, int m, const vector<int> &available,
                const vector<vector<int>> &alloc_mat,
                const vector<vector<int>> &need_mat,
                const vector<bool> &finished) {
  cout << "\n  +------- Current System State -------+" << endl;
  cout << "  Available : [ ";
  for (int j = 0; j < m; j++)
    cout << setw(2) << available[j] << " ";
  cout << "]" << endl;

  // Column headers
  cout << "\n           Allocation     Need" << endl;
  cout << "           ";
  for (int j = 0; j < m; j++)
    cout << "R" << j << " ";
  cout << "      ";
  for (int j = 0; j < m; j++)
    cout << "R" << j << " ";
  cout << endl;

  for (int i = 0; i < n; i++) {
    cout << "    P" << i;
    cout << (finished[i] ? "*" : " ");
    cout << " [ ";
    for (int j = 0; j < m; j++)
      cout << setw(2) << alloc_mat[i][j] << " ";
    cout << "]   [ ";
    for (int j = 0; j < m; j++)
      cout << setw(2) << need_mat[i][j] << " ";
    cout << "]" << endl;
  }
  cout << "  (* = finished)" << endl;
}

int main(int argc, char *argv[]) {
  if (argc < 2) {
    cerr << "Usage: " << argv[0] << " <input_file>" << endl;
    return 1;
  }

  srand(time(NULL));

  vector<int> nums = parse_file(argv[1]);
  if (nums.empty()) {
    cerr << "No valid numbers found in the file." << endl;
    return 1;
  }

  int m = nums[0]; // number of resources
  vector<int> total_res(m);
  for (int i = 0; i < m; i++)
    total_res[i] = nums[i + 1];

  int n = nums[m + 1]; // number of processes
  vector<vector<int>> max_mat(n, vector<int>(m));
  int idx = m + 2;
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < m; j++) {
      max_mat[i][j] = nums[idx++];
    }
  }

  vector<vector<int>> alloc_mat(n, vector<int>(m, 0));
  vector<vector<int>> need_mat = max_mat;
  vector<int> available = total_res;

  vector<bool> finished(n, false);
  vector<int> exec_order; // tracks actual completion order
  int processes_done = 0;
  int step = 0;
  const int MAX_STEPS = 1000;

  cout << "========================================" << endl;
  cout << "   Banker's Algorithm Simulation" << endl;
  cout << "========================================" << endl;
  cout << "  Processes : " << n << endl;
  cout << "  Resources : " << m << endl;
  cout << "  Total     : [ ";
  for (int j = 0; j < m; j++)
    cout << setw(2) << total_res[j] << " ";
  cout << "]" << endl;

  // Simulate until all processes finish or step limit reached
  while (processes_done < n && step < MAX_STEPS) {
    printState(n, m, available, alloc_mat, need_mat, finished);

    // Pick a random unfinished process
    int p;
    do {
      p = rand() % n;
    } while (finished[p]);

    // Request full remaining need for process p
    vector<int> req = need_mat[p];

    step++;
    cout << "\n  ---- Step " << step << " ----" << endl;
    cout << "  P" << p << " requests : [ ";
    for (int j = 0; j < m; j++)
      cout << setw(2) << req[j] << " ";
    cout << "]" << endl;

    // Banker's Step 1: Check Request <= Need
    bool valid_req = true;
    for (int j = 0; j < m; j++) {
      if (req[j] > need_mat[p][j]) {
        valid_req = false;
        break;
      }
    }
    if (!valid_req) {
      cout << "  -> ERROR: Request exceeds maximum claim for P" << p
           << ". Denied." << endl;
      continue;
    }

    // Banker's Step 2: Check Request <= Available
    bool can_grant = true;
    for (int j = 0; j < m; j++) {
      if (req[j] > available[j]) {
        can_grant = false;
        break;
      }
    }
    if (!can_grant) {
      cout << "  -> WAIT : Insufficient resources, P" << p << " must wait."
           << endl;
      continue;
    }

    // Banker's Step 3: Pretend to allocate (update all three together)
    for (int j = 0; j < m; j++) {
      available[j] -= req[j];
      alloc_mat[p][j] += req[j];
      need_mat[p][j] -= req[j];
    }

    // Banker's Step 4: Safety check
    vector<int> safe_seq;
    if (isSafe(n, m, available, max_mat, alloc_mat, safe_seq)) {
      cout << "  -> GRANT : Safe state confirmed." << endl;
      cout << "     Safe sequence: < ";
      for (int p_id : safe_seq)
        cout << "P" << p_id << " ";
      cout << ">" << endl;

      // Check if process p has finished (need is all zeros)
      bool is_finished = true;
      for (int j = 0; j < m; j++) {
        if (need_mat[p][j] > 0) {
          is_finished = false;
          break;
        }
      }

      if (is_finished) {
        cout << "  >> P" << p << " completed. Releasing: [ ";
        for (int j = 0; j < m; j++)
          cout << alloc_mat[p][j] << " ";
        cout << "]" << endl;
        for (int j = 0; j < m; j++) {
          available[j] += alloc_mat[p][j];
          alloc_mat[p][j] = 0;
        }
        finished[p] = true;
        processes_done++;
        exec_order.push_back(p);
        cout << "     Execution order: < ";
        for (int id : exec_order)
          cout << "P" << id << " ";
        cout << ">" << endl;
      }
    } else {
      cout << "  -> DENY  : Unsafe state detected, rolling back." << endl;
      // Rollback all three (symmetric to pretend step)
      for (int j = 0; j < m; j++) {
        available[j] += req[j];
        alloc_mat[p][j] -= req[j];
        need_mat[p][j] += req[j];
      }
    }
  }

  if (processes_done == n) {
    cout << "\n========================================" << endl;
    cout << "  All " << n << " processes finished successfully." << endl;
    cout << "  Total steps taken: " << step << endl;
    cout << "  Final execution order: < ";
    for (int id : exec_order)
      cout << "P" << id << " ";
    cout << ">" << endl;
    cout << "========================================" << endl;
  } else {
    cout << "\n  Simulation stopped after " << MAX_STEPS
         << " steps (not all processes finished)." << endl;
  }

  return 0;
}