
import psutil as ps
import os

class Bins:
    """
        The Bins class bins histogram data smartly. By dynamically managing
        available non-swap memory, we can maximize the size that our data
        structure (a Python `list` object, in this case) can attain before
        slowing other operations.

        #TODO Write a short whitepaper on why/how this works and why we're using
        it.
    """
    def __init__(self):
        self.mem = ps.Process(os.getpid())
    

    @staticmethod
    def sample():
        avail = ps.virtual_memory()
        print(avail)
        print(avail[1])


if __name__ == "__main__":
    Bins.sample()

"""
    Note that this should calculate percent of memory used relative to the
    start; i.e. our starting point is 0% memory used *by the histogram*.

    Then, for large numbers of iterations, we can write (or stream) the data to
    separate files and map the data to bins in each file. If we have n files and
    want to map into k bins, then we have n*k total bins; then, we simply have
    to reduce all n*k bins to k bins.
"""