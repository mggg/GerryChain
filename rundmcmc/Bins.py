
import psutil as ps
import os
import sys
import pickle


class Bins:
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
        pass


if __name__ == "__main__":
    b = Bins()
    col = []

    for i in range(0, 2**20):
        col += [i]
        print(b.current_usage)

"""
    Then, for large numbers of iterations, we can write (or stream) the data to
    separate files and map the data to bins in each file. If we have n files and
    want to map into k bins, then we have n*k total bins; then, we simply have
    to reduce all n*k bins to k bins.
"""
