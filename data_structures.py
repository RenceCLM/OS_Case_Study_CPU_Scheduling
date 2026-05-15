"""
Data structures module for CPU Scheduler.
Contains core data classes: Process and GanttBlock.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class Process:
    """
    Represents a single process to be scheduled.
    
    Attributes:
        pid (int): Process ID
        arrival (int): Arrival time (when process enters ready queue)
        burst (int): CPU burst time (total time needed to execute)
        priority (int): Priority level (default 0, lower = higher priority if enabled)
        color (Tuple): RGB color tuple for visualization
        
    Computed fields (set during simulation):
        start_time (int): When process started execution
        finish_time (int): When process completed
        remaining (int): Remaining burst time (for preemptive algorithms)
        waiting (int): Total time spent waiting
        turnaround (int): Total time from arrival to completion
        done (bool): Whether process has finished execution
    """
    pid: int
    arrival: int
    burst: int
    priority: int = 0
    color: Tuple = (67, 120, 220)
    
    # Computed fields (set during simulation)
    start_time: int = -1
    finish_time: int = -1
    remaining: int = 0
    waiting: int = 0
    turnaround: int = 0
    done: bool = False

    def __post_init__(self):
        """Initialize remaining burst time equal to total burst time."""
        self.remaining = self.burst


@dataclass
class GanttBlock:
    """
    Represents one colored segment/block in the Gantt chart.
    Shows when a process runs on the CPU.
    
    Attributes:
        pid (int): Process ID that was executing
        start (int): Start time of this execution segment
        end (int): End time of this execution segment
        color (Tuple): RGB color for visualization
    """
    pid: int
    start: int
    end: int
    color: Tuple
