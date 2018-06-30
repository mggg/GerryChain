
import psutil as ps
import os
import sys
import pickle
import collections


class DataStore:
    """
        The DataStore class stores data quickly and small-ly (if that's a word).
        Lightweight and easy to use, this is the perfect solution for users who
        need to store massive amounts of data efficiently (see running 2**31
        steps on the chain and storing every data point).

        TODO Write a short whitepaper on why/how this works and why we're using
        it. (!!!!!!!!!!!!!!!!!!!!!)

        TODO The number of stores should be a power of two so we can do some
        mapreduce magic.
    """
    def __init__(self, data=None):
        """
            Initialize.
        """
        """
            Properties.
                :mem:       Dictionary containing vmem information.
                :start:     Amount of memory we start out using.
                :_data:     List of objects to be saved.
                :_pickles:  Pickled objects represented as `bytes` objects.
                            This just holds internal references to them, and
                            they'll be written to file when 
        """
        mem = ps.virtual_memory()
        self.mem = {
            "total": mem[0],
            "available": mem[1],
            "free": mem[4],
            "active": mem[5]
        }

        # Uses the psutil Process constructor to get the current resident set
        # size (rss) at the start of the process.
        self.start = ps.Process(os.getpid()).memory_info().rss

        # Initialize the (private) internal `_data` and `_pickles` collections.
        # Fortunately, these are faster at adding/inserting/popping things. See
        # http://bit.ly/2MzkuMD for more details on this.
        self._data = collections.deque()
        self._pickles = collections.deque() if data is None else collections.deque(data)

    @property
    def usage(self):
        """
            Readonly property that returns the percentage of memory used by this
            process.
        """
        current = ps.Process(os.getpid()).memory_info().rss
        return 100 * (current - self.start) / self.mem["available"]

    @property
    def data(self):
        """
            Readonly property that returns a tuple containing the length of
            `_data` and the most recent item added to `_data`. This will mostly
            be used for diagnostic purposes, but can be useful otherwise.
        """
        return (len(self._data), self._data[-1])

    def add(self, obj=None):
        """
            Adds `obj` to the list of data. Also checks current memory
            pressure to see whether to pickle objects or write existing pickled
            objects in `_pickles` to file.

            Note that `obj` should be Pickleable, otherwise DataStore will throw
            a `pickle.PicklingError` error. Take a look here to find more info
            about object pickling: http://bit.ly/2yQV9ff.

                :obj:   (Pickleable) object added to _data.
        """
        # Check current data pressure.
        self._data.append(obj)
    
    def _pickle(self):
        """
            Compresses the data in _data, writes the data to a file, and flushes
            _data.
        """
        pass

    def _pickle_to_file(self):
        pass


if __name__ == "__main__":
    ds = DataStore()

    for i in range(0, 2**20):
        ds.add(i)
        print(ds.data)

"""
    Then, for large numbers of iterations, we can write (or stream) the data to
    separate files and map the data to bins in each file. If we have n files and
    want to map into k bins, then we have n*k total bins; then, we simply have
    to reduce all n*k bins to k bins.
"""
