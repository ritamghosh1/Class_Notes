#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <queue>
#include <sstream>
#include <string>
#include <vector>

using namespace std;

// Represents a single CPU or I/O burst
struct Burst {
  char type; // 'C' for CPU, 'I' for I/O
  int duration;
};

// Represents a job/process
struct Job {
  int id;
  int priority; // lower number = higher priority
  int arrival_time;
  vector<Burst> bursts; // alternating CPU, I/O, CPU, I/O, ..., CPU
};

// Runtime state of a job during simulation
struct JobState {
  int job_id;
  int priority;
  int arrival_time;

  vector<Burst> bursts;  // full burst list
  int current_burst_idx; // index into bursts[]
  int remaining;         // remaining time in current burst

  int completion_time;
  int turnaround_time;
  int waiting_time;

  // Timestamps for tracking
  int last_ready_time; // when the job last entered the ready queue

  bool is_finished() const { return current_burst_idx >= (int)bursts.size(); }
};

// ───────────────────────────────────────────────────
// File Parsing
// ───────────────────────────────────────────────────
vector<Job> parse_jobs(const string &filename) {
  ifstream file(filename);
  if (!file) {
    cerr << "Error opening file: " << filename << endl;
    exit(1);
  }

  vector<Job> jobs;
  string line;
  while (getline(file, line)) {
    if (line.empty())
      continue;

    istringstream iss(line);
    Job job;
    int val;

    iss >> job.id >> job.priority >> job.arrival_time;

    bool is_cpu = true; // first burst is always CPU
    while (iss >> val) {
      if (val == -1)
        break;
      Burst b;
      b.type = is_cpu ? 'C' : 'I';
      b.duration = val;
      job.bursts.push_back(b);
      is_cpu = !is_cpu;
    }
    jobs.push_back(job);
  }
  return jobs;
}

// ───────────────────────────────────────────────────
// Helper: Initialize job states from jobs
// ───────────────────────────────────────────────────
vector<JobState> init_states(const vector<Job> &jobs) {
  vector<JobState> states;
  for (const auto &j : jobs) {
    JobState s;
    s.job_id = j.id;
    s.priority = j.priority;
    s.arrival_time = j.arrival_time;
    s.bursts = j.bursts;
    s.current_burst_idx = 0;
    s.remaining = j.bursts.empty() ? 0 : j.bursts[0].duration;
    s.completion_time = 0;
    s.turnaround_time = 0;
    s.waiting_time = 0;
    s.last_ready_time = j.arrival_time;
    states.push_back(s);
  }
  return states;
}

// ───────────────────────────────────────────────────
// Helper: Print results table
// ───────────────────────────────────────────────────
void print_results(const string &algo_name, const vector<JobState> &states) {
  cout << "\n  ╔══════════════════════════════════════════════════════╗"
       << endl;
  cout << "  ║  " << left << setw(52) << algo_name << "║" << endl;
  cout << "  ╠══════════════════════════════════════════════════════╣" << endl;
  cout << "  ║  " << left << setw(8) << "Job" << setw(12) << "Arrival"
       << setw(14) << "Completion" << setw(12) << "TAT" << setw(8) << "WT"
       << "║" << endl;
  cout << "  ╠══════════════════════════════════════════════════════╣" << endl;

  double total_tat = 0, total_wt = 0;
  for (const auto &s : states) {
    cout << "  ║  " << left << setw(8) << s.job_id << setw(12) << s.arrival_time
         << setw(14) << s.completion_time << setw(12) << s.turnaround_time
         << setw(8) << s.waiting_time << "║" << endl;
    total_tat += s.turnaround_time;
    total_wt += s.waiting_time;
  }

  int n = states.size();
  cout << "  ╠══════════════════════════════════════════════════════╣" << endl;
  cout << "  ║  " << left << setw(34) << "Average TAT:" << setw(18) << fixed
       << setprecision(2) << (total_tat / n) << "║" << endl;
  cout << "  ║  " << left << setw(34) << "Average WT:" << setw(18) << fixed
       << setprecision(2) << (total_wt / n) << "║" << endl;
  cout << "  ╚══════════════════════════════════════════════════════╝" << endl;
}

// ───────────────────────────────────────────────────
// Print Gantt Chart
// ───────────────────────────────────────────────────
void print_gantt(const vector<pair<string, int>> &gantt) {
  cout << "\n  Gantt Chart:" << endl;
  cout << "  |";
  for (const auto &g : gantt) {
    int width = max((int)g.first.size() + 2, 5);
    cout << " " << left << setw(width - 2) << g.first << " |";
  }
  cout << endl;

  cout << "  0";
  for (const auto &g : gantt) {
    int width = max((int)g.first.size() + 2, 5);
    cout << right << setw(width + 1) << g.second;
  }
  cout << endl;
}

// ═══════════════════════════════════════════════════
// FCFS Scheduling
// ═══════════════════════════════════════════════════
void schedule_fcfs(const vector<Job> &jobs) {
  vector<JobState> states = init_states(jobs);

  // Sort by arrival time, then by job id for tie-breaking
  sort(states.begin(), states.end(), [](const JobState &a, const JobState &b) {
    if (a.arrival_time != b.arrival_time)
      return a.arrival_time < b.arrival_time;
    return a.job_id < b.job_id;
  });

  int time = 0;
  int done = 0;
  int n = states.size();
  vector<pair<string, int>> gantt;

  // I/O completion events: (completion_time, index in states)
  // We use a priority queue (min-heap)
  priority_queue<pair<int, int>, vector<pair<int, int>>,
                 greater<pair<int, int>>>
      io_queue;

  // Ready queue (FIFO for FCFS)
  queue<int> ready_queue;

  // Track which jobs have arrived and been added to ready queue
  vector<bool> arrived(n, false);

  while (done < n) {
    // Add newly arrived jobs to ready queue
    for (int i = 0; i < n; i++) {
      if (!arrived[i] && states[i].arrival_time <= time) {
        arrived[i] = true;
        ready_queue.push(i);
        states[i].last_ready_time = time;
      }
    }

    // Check I/O completions
    while (!io_queue.empty() && io_queue.top().first <= time) {
      int idx = io_queue.top().second;
      int io_end = io_queue.top().first;
      io_queue.pop();
      states[idx].current_burst_idx++;
      if (states[idx].is_finished()) {
        states[idx].completion_time = io_end;
        states[idx].turnaround_time = io_end - states[idx].arrival_time;
        done++;
      } else {
        states[idx].remaining =
            states[idx].bursts[states[idx].current_burst_idx].duration;
        ready_queue.push(idx);
        states[idx].last_ready_time = time;
      }
    }

    if (ready_queue.empty()) {
      // Fast-forward time
      int next_time = INT_MAX;
      for (int i = 0; i < n; i++) {
        if (!arrived[i])
          next_time = min(next_time, states[i].arrival_time);
      }
      if (!io_queue.empty())
        next_time = min(next_time, io_queue.top().first);

      if (next_time == INT_MAX)
        break;

      gantt.push_back({"IDLE", next_time});
      time = next_time;
      continue;
    }

    int idx = ready_queue.front();
    ready_queue.pop();

    // Accumulate waiting time
    states[idx].waiting_time += (time - states[idx].last_ready_time);

    // Run the entire current CPU burst (non-preemptive)
    int burst_time = states[idx].remaining;
    time += burst_time;
    gantt.push_back({"J" + to_string(states[idx].job_id), time});

    // Move to next burst
    states[idx].current_burst_idx++;
    states[idx].remaining = 0;

    if (states[idx].is_finished()) {
      // Job completed
      states[idx].completion_time = time;
      states[idx].turnaround_time = time - states[idx].arrival_time;
      done++;
    } else {
      // Next burst is I/O
      Burst &io = states[idx].bursts[states[idx].current_burst_idx];
      io_queue.push({time + io.duration, idx});
    }

    // Check for new arrivals during the burst
    for (int i = 0; i < n; i++) {
      if (!arrived[i] && states[i].arrival_time <= time) {
        arrived[i] = true;
        ready_queue.push(i);
        states[i].last_ready_time = states[i].arrival_time;
      }
    }

    // Check I/O completions again
    while (!io_queue.empty() && io_queue.top().first <= time) {
      int io_idx = io_queue.top().second;
      int io_end = io_queue.top().first;
      io_queue.pop();
      states[io_idx].current_burst_idx++;
      if (states[io_idx].is_finished()) {
        states[io_idx].completion_time = io_end;
        states[io_idx].turnaround_time = io_end - states[io_idx].arrival_time;
        done++;
      } else {
        states[io_idx].remaining =
            states[io_idx].bursts[states[io_idx].current_burst_idx].duration;
        ready_queue.push(io_idx);
        states[io_idx].last_ready_time = time;
      }
    }
  }

  print_gantt(gantt);

  // Sort by job_id for display
  sort(states.begin(), states.end(), [](const JobState &a, const JobState &b) {
    return a.job_id < b.job_id;
  });
  print_results("FCFS (First Come First Serve)", states);
}

// ═══════════════════════════════════════════════════
// Non-Preemptive Priority Scheduling
// ═══════════════════════════════════════════════════
void schedule_priority(const vector<Job> &jobs) {
  vector<JobState> states = init_states(jobs);
  int n = states.size();
  int time = 0, done = 0;
  vector<pair<string, int>> gantt;

  priority_queue<pair<int, int>, vector<pair<int, int>>,
                 greater<pair<int, int>>>
      io_queue;

  // Ready "queue" - we pick highest priority (lowest number) each time
  vector<bool> in_ready(n, false);
  vector<bool> arrived(n, false);
  vector<bool> completed(n, false);

  while (done < n) {
    // Add newly arrived jobs
    for (int i = 0; i < n; i++) {
      if (!arrived[i] && states[i].arrival_time <= time) {
        arrived[i] = true;
        in_ready[i] = true;
        states[i].last_ready_time = states[i].arrival_time;
      }
    }

    // Check I/O completions
    while (!io_queue.empty() && io_queue.top().first <= time) {
      int idx = io_queue.top().second;
      int io_end = io_queue.top().first;
      io_queue.pop();
      states[idx].current_burst_idx++;
      if (states[idx].is_finished()) {
        states[idx].completion_time = io_end;
        states[idx].turnaround_time = io_end - states[idx].arrival_time;
        completed[idx] = true;
        done++;
      } else {
        states[idx].remaining =
            states[idx].bursts[states[idx].current_burst_idx].duration;
        in_ready[idx] = true;
        states[idx].last_ready_time = time;
      }
    }

    // Pick highest priority (lowest priority number) from ready
    int best = -1;
    for (int i = 0; i < n; i++) {
      if (in_ready[i] && !completed[i]) {
        if (best == -1 || states[i].priority < states[best].priority ||
            (states[i].priority == states[best].priority &&
             states[i].arrival_time < states[best].arrival_time)) {
          best = i;
        }
      }
    }

    if (best == -1) {
      // Fast-forward
      int next_time = INT_MAX;
      for (int i = 0; i < n; i++) {
        if (!arrived[i])
          next_time = min(next_time, states[i].arrival_time);
      }
      if (!io_queue.empty())
        next_time = min(next_time, io_queue.top().first);

      if (next_time == INT_MAX)
        break;

      gantt.push_back({"IDLE", next_time});
      time = next_time;
      continue;
    }

    in_ready[best] = false;
    states[best].waiting_time += (time - states[best].last_ready_time);

    int burst_time = states[best].remaining;
    time += burst_time;
    gantt.push_back({"J" + to_string(states[best].job_id), time});

    states[best].current_burst_idx++;
    states[best].remaining = 0;

    if (states[best].is_finished()) {
      states[best].completion_time = time;
      states[best].turnaround_time = time - states[best].arrival_time;
      completed[best] = true;
      done++;
    } else {
      Burst &io = states[best].bursts[states[best].current_burst_idx];
      io_queue.push({time + io.duration, best});
    }

    // Check arrivals during burst
    for (int i = 0; i < n; i++) {
      if (!arrived[i] && states[i].arrival_time <= time) {
        arrived[i] = true;
        in_ready[i] = true;
        states[i].last_ready_time = states[i].arrival_time;
      }
    }

    // Check I/O completions
    while (!io_queue.empty() && io_queue.top().first <= time) {
      int idx = io_queue.top().second;
      int io_end = io_queue.top().first;
      io_queue.pop();
      states[idx].current_burst_idx++;
      if (states[idx].is_finished()) {
        states[idx].completion_time = io_end;
        states[idx].turnaround_time = io_end - states[idx].arrival_time;
        completed[idx] = true;
        done++;
      } else {
        states[idx].remaining =
            states[idx].bursts[states[idx].current_burst_idx].duration;
        in_ready[idx] = true;
        states[idx].last_ready_time = time;
      }
    }
  }

  print_gantt(gantt);

  sort(states.begin(), states.end(), [](const JobState &a, const JobState &b) {
    return a.job_id < b.job_id;
  });
  print_results("Non-Preemptive Priority", states);
}

// ═══════════════════════════════════════════════════
// Round Robin Scheduling (quantum = 16)
// ═══════════════════════════════════════════════════
void schedule_rr(const vector<Job> &jobs, int quantum) {
  vector<JobState> states = init_states(jobs);
  int n = states.size();
  int time = 0, done = 0;
  vector<pair<string, int>> gantt;

  priority_queue<pair<int, int>, vector<pair<int, int>>,
                 greater<pair<int, int>>>
      io_queue;

  queue<int> ready_queue;
  vector<bool> arrived(n, false);
  vector<bool> in_queue(n, false);
  vector<bool> completed(n, false);

  // Sort indices by arrival time for consistent ordering
  vector<int> sorted_idx(n);
  for (int i = 0; i < n; i++)
    sorted_idx[i] = i;
  sort(sorted_idx.begin(), sorted_idx.end(), [&](int a, int b) {
    if (states[a].arrival_time != states[b].arrival_time)
      return states[a].arrival_time < states[b].arrival_time;
    return states[a].job_id < states[b].job_id;
  });

  auto add_arrivals = [&](int t) {
    for (int i : sorted_idx) {
      if (!arrived[i] && states[i].arrival_time <= t) {
        arrived[i] = true;
        in_queue[i] = true;
        ready_queue.push(i);
        states[i].last_ready_time = states[i].arrival_time;
      }
    }
  };

  auto process_io = [&](int t) {
    // Collect all I/O completions at or before time t
    vector<pair<int, int>> io_done; // (completion_time, index)
    while (!io_queue.empty() && io_queue.top().first <= t) {
      io_done.push_back(io_queue.top());
      io_queue.pop();
    }
    for (auto &p : io_done) {
      int io_end = p.first;
      int idx = p.second;
      states[idx].current_burst_idx++;
      if (states[idx].is_finished()) {
        states[idx].completion_time = io_end;
        states[idx].turnaround_time = io_end - states[idx].arrival_time;
        completed[idx] = true;
        done++;
      } else {
        states[idx].remaining =
            states[idx].bursts[states[idx].current_burst_idx].duration;
        in_queue[idx] = true;
        ready_queue.push(idx);
        states[idx].last_ready_time = t;
      }
    }
  };

  while (done < n) {
    add_arrivals(time);
    process_io(time);

    if (ready_queue.empty()) {
      int next_time = INT_MAX;
      for (int i = 0; i < n; i++) {
        if (!arrived[i])
          next_time = min(next_time, states[i].arrival_time);
      }
      if (!io_queue.empty())
        next_time = min(next_time, io_queue.top().first);

      if (next_time == INT_MAX)
        break;

      gantt.push_back({"IDLE", next_time});
      time = next_time;
      continue;
    }

    int idx = ready_queue.front();
    ready_queue.pop();
    in_queue[idx] = false;

    states[idx].waiting_time += (time - states[idx].last_ready_time);

    int run_time = min(quantum, states[idx].remaining);
    states[idx].remaining -= run_time;
    time += run_time;
    gantt.push_back({"J" + to_string(states[idx].job_id), time});

    // Add arrivals and I/O completions that occurred during this burst
    add_arrivals(time);
    process_io(time);

    if (states[idx].remaining == 0) {
      // Current CPU burst finished
      states[idx].current_burst_idx++;

      if (states[idx].is_finished()) {
        states[idx].completion_time = time;
        states[idx].turnaround_time = time - states[idx].arrival_time;
        completed[idx] = true;
        done++;
      } else {
        // Next burst is I/O
        Burst &io = states[idx].bursts[states[idx].current_burst_idx];
        io_queue.push({time + io.duration, idx});
      }
    } else {
      // Preempted — put back in ready queue
      in_queue[idx] = true;
      ready_queue.push(idx);
      states[idx].last_ready_time = time;
    }
  }

  print_gantt(gantt);

  sort(states.begin(), states.end(), [](const JobState &a, const JobState &b) {
    return a.job_id < b.job_id;
  });
  print_results("Round Robin (quantum=" + to_string(quantum) + ")", states);
}

// ═══════════════════════════════════════════════════
// Comparison Summary
// ═══════════════════════════════════════════════════
void print_comparison(const vector<Job> &jobs) {
  // Run all three and collect averages
  // We'll re-run them and capture the averages

  cout << "\n  ╔══════════════════════════════════════════════════════╗"
       << endl;
  cout << "  ║         Scheduling Algorithm Comparison             ║" << endl;
  cout << "  ╠══════════════════════════════════════════════════════╣" << endl;
  cout << "  ║  Algorithm              Avg TAT      Avg WT         ║" << endl;
  cout << "  ╠══════════════════════════════════════════════════════╣" << endl;

  auto calc_averages =
      [](const vector<JobState> &states) -> pair<double, double> {
    double total_tat = 0, total_wt = 0;
    for (const auto &s : states) {
      total_tat += s.turnaround_time;
      total_wt += s.waiting_time;
    }
    int n = states.size();
    return {total_tat / n, total_wt / n};
  };

  // We need to re-simulate to get the states with results
  // For simplicity, we just print a note that detailed results are above
  cout << "  ║  (See detailed results above for each algorithm)    ║" << endl;
  cout << "  ╚══════════════════════════════════════════════════════╝" << endl;
}

// ═══════════════════════════════════════════════════
// Print Job Profiles
// ═══════════════════════════════════════════════════
void print_jobs(const vector<Job> &jobs) {
  cout << "\n  Loaded " << jobs.size() << " job profiles:" << endl;
  cout << "  " << string(60, '-') << endl;
  for (const auto &j : jobs) {
    cout << "  Job " << j.id << " | Priority: " << j.priority
         << " | Arrival: " << j.arrival_time << " | Bursts: ";
    for (size_t i = 0; i < j.bursts.size(); i++) {
      if (i > 0)
        cout << " -> ";
      cout << (j.bursts[i].type == 'C' ? "CPU(" : "I/O(")
           << j.bursts[i].duration << ")";
    }
    cout << endl;
  }
  cout << "  " << string(60, '-') << endl;
}

// ═══════════════════════════════════════════════════
int main(int argc, char *argv[]) {
  if (argc < 2) {
    cerr << "Usage: " << argv[0] << " <job_profile_file>" << endl;
    return 1;
  }

  vector<Job> jobs = parse_jobs(argv[1]);
  if (jobs.empty()) {
    cerr << "No jobs found in file." << endl;
    return 1;
  }

  cout << "========================================" << endl;
  cout << "     CPU Scheduler Simulation" << endl;
  cout << "========================================" << endl;

  print_jobs(jobs);

  cout << "\n\n  ===== 1. FCFS Scheduling =====" << endl;
  schedule_fcfs(jobs);

  cout << "\n\n  ===== 2. Non-Preemptive Priority Scheduling =====" << endl;
  schedule_priority(jobs);

  cout << "\n\n  ===== 3. Round Robin Scheduling (Quantum = 16) =====" << endl;
  schedule_rr(jobs, 16);

  cout << endl;
  return 0;
}
