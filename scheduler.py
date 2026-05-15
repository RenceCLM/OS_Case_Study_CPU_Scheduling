"""
CPU Scheduling Algorithms module.
Implements 7 classic CPU scheduling algorithms with detailed documentation.

All functions return:
    - gantt_blocks: List[GanttBlock] - Timeline of process execution
    - completed_procs: List[Process] - Processes sorted by completion
"""

import copy
from typing import List
from data_structures import Process, GanttBlock


# ─── FCFS: First-Come, First-Served ───────────────────────────────────────────

def run_fcfs(procs: List[Process]):
    """
    FCFS (First-Come, First-Served) Scheduling - Non-Preemptive.
    
    Algorithm:
        1. Sort processes by arrival time (ties broken by PID)
        2. Run each process to completion in order
        3. No preemption; process keeps CPU until burst completes

    
    Returns:
        gantt_blocks: Timeline of execution
        procs: Processes in completion order
    """
    procs = sorted(procs, key=lambda p: (p.arrival, p.pid))
    t, blocks = 0, []
    
    for p in procs:
        # If CPU is idle, advance time to process arrival
        if t < p.arrival:
            t = p.arrival
            
        p.start_time = t
        blocks.append(GanttBlock(p.pid, t, t + p.burst, p.color))
        t += p.burst
        
        # Calculate metrics
        p.finish_time = t
        p.turnaround = p.finish_time - p.arrival  # Total time in system
        p.waiting = p.turnaround - p.burst  # Time waiting before execution
        p.done = True
        
    return blocks, procs


# ─── SJF: Shortest Job First ─────────────────────────────────────────────────

def run_sjf(procs: List[Process]):
    """
    SJF (Shortest Job First) Scheduling - Non-Preemptive.
    
    Algorithm:
        1. Among all arrived processes, select one with smallest burst time
        2. Run it to completion (non-preemptive)
        3. Repeat until all processes complete
    
    Returns:
        gantt_blocks: Timeline of execution
        procs: Processes in completion order
    """
    t, done, blocks = 0, [], []
    remaining = list(sorted(procs, key=lambda p: (p.arrival, p.pid)))
    
    while remaining:
        # Get all processes that have arrived by time t
        available = [p for p in remaining if p.arrival <= t]
        
        # If none arrived yet, advance time to next arrival
        if not available:
            t = min(p.arrival for p in remaining)
            available = [p for p in remaining if p.arrival <= t]
        
        # Select process with shortest burst; ties broken by PID
        p = min(available, key=lambda x: (x.burst, x.pid))
        
        p.start_time = t
        blocks.append(GanttBlock(p.pid, t, t + p.burst, p.color))
        t += p.burst
        
        # Calculate metrics
        p.finish_time = t
        p.turnaround = p.finish_time - p.arrival
        p.waiting = p.turnaround - p.burst
        p.done = True
        
        remaining.remove(p)
        done.append(p)
        
    return blocks, done


# ─── SRTF: Shortest Remaining Time First ─────────────────────────────────────

def run_srtf(procs: List[Process]):
    """
    SRTF (Shortest Remaining Time First) Scheduling - Preemptive.
    
    Algorithm:
        1. At each time tick, select process with least remaining burst
        2. Run for 1 time unit
        3. Preempt if a shorter job arrives or becomes available
        4. Adjacent same-PID blocks are merged to reduce Gantt noise
    
    Returns:
        gantt_blocks: Timeline of execution (merged)
        procs: Processes in completion order
    """
    procs_work = [
        copy.deepcopy(p) for p in sorted(procs, key=lambda p: (p.arrival, p.pid))
    ]
    t, blocks, done = 0, [], []
    end_t = sum(p.burst for p in procs_work) + max(p.arrival for p in procs_work) + 10
    
    for _ in range(end_t * 3):
        # Get all arrived processes not yet done
        available = [p for p in procs_work if p.arrival <= t and not p.done]
        
        if not available:
            if all(p.done for p in procs_work):
                break
            t += 1
            continue
        
        # Select process with smallest remaining time; ties broken by PID
        p = min(available, key=lambda x: (x.remaining, x.pid))
        
        if p.start_time == -1:
            p.start_time = t
        
        # Merge with previous block if same process
        if blocks and blocks[-1].pid == p.pid:
            blocks[-1].end = t + 1
        else:
            blocks.append(GanttBlock(p.pid, t, t + 1, p.color))
        
        p.remaining -= 1
        t += 1
        
        # Check if process is done
        if p.remaining == 0:
            p.finish_time = t
            p.turnaround = t - p.arrival
            p.waiting = p.turnaround - p.burst
            p.done = True
            done.append(p)
        
        if all(p.done for p in procs_work):
            break
    
    # Merge adjacent blocks with same PID
    merged = []
    for b in blocks:
        if merged and merged[-1].pid == b.pid:
            merged[-1].end = b.end
        else:
            merged.append(b)
    
    return merged, done


# ─── Round Robin ─────────────────────────────────────────────────────────────

def run_rr(procs: List[Process], quantum: int):
    """
    Round Robin Scheduling - Preemptive.
    
    Algorithm:
        1. Maintain a ready queue of processes
        2. Allocate each process CPU time up to 'quantum' units
        3. After quantum expires or process completes, move to back of queue
        4. Newly arrived processes enqueued before returning process re-queues
    
    
    Args:
        procs: List of processes
        quantum: Time slice per process (units)
    
    Returns:
        gantt_blocks: Timeline of execution
        procs: Processes in completion order
    """
    procs_work = sorted([copy.deepcopy(p) for p in procs], key=lambda p: (p.arrival, p.pid))
    t, queue, blocks, done, arrived = 0, [], [], [], set()
    
    def enqueue_new(time):
        """Enqueue all processes that have just arrived."""
        for p in procs_work:
            if p.pid not in arrived and p.arrival <= time and not p.done:
                queue.append(p)
                arrived.add(p.pid)
    
    enqueue_new(0)
    safety = 0  # Prevent infinite loops
    
    while (queue or any(not p.done for p in procs_work)) and safety < 100_000:
        safety += 1
        
        if not queue:
            # Advance time to next process arrival
            t = min(p.arrival for p in procs_work if not p.done)
            enqueue_new(t)
        
        # Dequeue front process
        p = queue.pop(0)
        
        if p.start_time == -1:
            p.start_time = t
        
        # Run for up to quantum time units
        run = min(quantum, p.remaining)
        blocks.append(GanttBlock(p.pid, t, t + run, p.color))
        t += run
        p.remaining -= run
        
        # Enqueue newly arrived processes before re-queuing this one
        enqueue_new(t)
        
        if p.remaining == 0:
            # Process completed
            p.finish_time = t
            p.turnaround = t - p.arrival
            p.waiting = p.turnaround - p.burst
            p.done = True
            done.append(p)
        else:
            # Re-enqueue for next round
            queue.append(p)
    
    return blocks, done


# ─── Priority Scheduling (Non-Preemptive) ────────────────────────────────────

def run_priority_np(procs: List[Process], lower_is_higher: bool):
    """
    Priority Scheduling - Non-Preemptive.
    
    Algorithm:
        1. Among all arrived processes, select highest priority one
        2. Run to completion (non-preemptive)
        3. Repeat until all complete
    
    
    Args:
        procs: List of processes
        lower_is_higher: True if lower value = higher priority, False otherwise
    
    Returns:
        gantt_blocks: Timeline of execution
        procs: Processes in completion order
    """
    procs_work = sorted([copy.deepcopy(p) for p in procs], key=lambda p: (p.arrival, p.pid))
    t, remaining, blocks, done = 0, list(procs_work), [], []
    
    while remaining:
        # Get all arrived processes
        available = [p for p in remaining if p.arrival <= t]
        
        if not available:
            t = min(p.arrival for p in remaining)
            available = [p for p in remaining if p.arrival <= t]
        
        # Select highest priority process (lower value = higher priority)
        key = (lambda x: (x.priority, x.pid)) if lower_is_higher else (lambda x: (-x.priority, x.pid))
        p = min(available, key=key)
        
        p.start_time = t
        blocks.append(GanttBlock(p.pid, t, t + p.burst, p.color))
        t += p.burst
        
        # Calculate metrics
        p.finish_time = t
        p.turnaround = t - p.arrival
        p.waiting = p.turnaround - p.burst
        p.done = True
        
        remaining.remove(p)
        done.append(p)
    
    return blocks, done


# ─── Priority Scheduling (Preemptive) ────────────────────────────────────────

def run_priority_p(procs: List[Process], lower_is_higher: bool):
    """
    Priority Scheduling - Preemptive.
    
    Algorithm:
        1. At each time tick, select highest priority arrived process
        2. Run for 1 unit
        3. Preempt if higher priority process arrives
        4. Adjacent same-PID blocks are merged
    
    Args:
        procs: List of processes
        lower_is_higher: True if lower value = higher priority, False otherwise
    
    Returns:
        gantt_blocks: Timeline of execution (merged)
        procs: Processes in completion order
    """
    procs_work = sorted([copy.deepcopy(p) for p in procs], key=lambda p: (p.arrival, p.pid))
    t, blocks, done = 0, [], []
    end_t = max(p.arrival for p in procs_work) + sum(p.burst for p in procs_work) + 1
    key_fn = (lambda x: (x.priority, x.pid)) if lower_is_higher else (lambda x: (-x.priority, x.pid))
    
    for _ in range(end_t * 2):
        # Get all arrived processes not yet done
        available = [p for p in procs_work if p.arrival <= t and not p.done]
        
        if not available:
            if all(p.done for p in procs_work):
                break
            t += 1
            continue
        
        # Select highest priority process
        p = min(available, key=key_fn)
        
        if p.start_time == -1:
            p.start_time = t
        
        # Merge with previous block if same process
        if blocks and blocks[-1].pid == p.pid:
            blocks[-1].end = t + 1
        else:
            blocks.append(GanttBlock(p.pid, t, t + 1, p.color))
        
        p.remaining -= 1
        t += 1
        
        if p.remaining == 0:
            p.finish_time = t
            p.turnaround = t - p.arrival
            p.waiting = p.turnaround - p.burst
            p.done = True
            done.append(p)
        
        if all(p.done for p in procs_work):
            break
    
    # Merge adjacent blocks with same PID
    merged = []
    for b in blocks:
        if merged and merged[-1].pid == b.pid:
            merged[-1].end = b.end
        else:
            merged.append(b)
    
    return merged, done


# ─── Priority + Round Robin ──────────────────────────────────────────────────

def run_priority_rr(procs: List[Process], quantum: int, lower_is_higher: bool):
    """
    Priority Scheduling with Round Robin - Preemptive.
    
    Algorithm:
        1. Maintain queue ordered by priority
        2. Each process gets quantum time units
        3. After quantum, re-insert by priority order
        4. Newly arrived processes insert by priority
    
    Args:
        procs: List of processes
        quantum: Time slice per process (units)
        lower_is_higher: True if lower value = higher priority, False otherwise
    
    Returns:
        gantt_blocks: Timeline of execution
        procs: Processes in completion order
    """
    procs_work = sorted([copy.deepcopy(p) for p in procs], key=lambda p: (p.arrival, p.pid))
    t, blocks, done, arrived, queue = 0, [], [], set(), []
    key_fn = (lambda x: (x.priority, x.pid)) if lower_is_higher else (lambda x: (-x.priority, x.pid))
    
    def enqueue_new(time):
        """Enqueue newly arrived processes by priority order."""
        newly = [p for p in procs_work if p.pid not in arrived and p.arrival <= time and not p.done]
        newly.sort(key=key_fn)
        for p in newly:
            queue.append(p)
            arrived.add(p.pid)
    
    enqueue_new(0)
    safety = 0
    
    while (queue or any(not p.done for p in procs_work)) and safety < 100_000:
        safety += 1
        
        if not queue:
            t = min(p.arrival for p in procs_work if not p.done)
            enqueue_new(t)
        
        p = queue.pop(0)
        
        if p.start_time == -1:
            p.start_time = t
        
        # Run for up to quantum time units
        run = min(quantum, p.remaining)
        blocks.append(GanttBlock(p.pid, t, t + run, p.color))
        t += run
        p.remaining -= run
        
        # Enqueue newly arrived processes
        enqueue_new(t)
        
        if p.remaining == 0:
            p.finish_time = t
            p.turnaround = t - p.arrival
            p.waiting = p.turnaround - p.burst
            p.done = True
            done.append(p)
        else:
            # Re-insert by priority order (maintain sorted queue)
            insert_idx = len(queue)
            for i, q in enumerate(queue):
                if key_fn(p) < key_fn(q):
                    insert_idx = i
                    break
            queue.insert(insert_idx, p)
    
    return blocks, done
