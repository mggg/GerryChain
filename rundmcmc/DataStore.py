
import psutil as ps
import os
import sys
import pickle


class DataStore:
    """
        The Bins class bins histogram data smartly.

        TODO Write a short whitepaper on why/how this works and why we're using
        it. (!!!!!!!!!!!!!!!!!!!!!)

        TODO The number of stores should be a power of two so we can do some
        mapreduce magic.
    """
    def __init__(self):
        """
            Initialize.
        """
        """
            Properties.
                :mem:   Dictionary containing vmem information.
                :start: Amount of memory we start out using.
        """
        mem = ps.virtual_memory()
        self.mem = {
            "total": mem[0],
            "available": mem[1],
            "free": mem[4],
            "active": mem[5]
        }

        self.start = ps.Process(os.getpid()).memory_info().rss

    @property
    def usage(self):
        """
            Readonly property that returns the amount of memory used as a
            percentage.
        """
        current = ps.Process(os.getpid()).memory_info().rss
        return 100 * (current - self.start) / self.mem["available"]


if __name__ == "__main__":
    b = DataStore()
    col = []

    for i in range(0, 2**20):
        print(b.usage)

"""
    Then, for large numbers of iterations, we can write (or stream) the data to
    separate files and map the data to bins in each file. If we have n files and
    want to map into k bins, then we have n*k total bins; then, we simply have
    to reduce all n*k bins to k bins.
"""
