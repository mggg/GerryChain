
import psutil as ps
import os
import sys
import pickle as pkl
import pickletools as pklt
from collections import deque


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

        TODO Some file i/o.

        TODO Get data out of the pickles.
    """
    def __init__(self, data=None, epsilon=15):
        """
            Initialize.
                :data:      Initial data.
                :epsilon:   Default memory threshold that must be eclipsed before
                            pickling/filewriting.
        """
        """
            Properties.
                :mem:       Dictionary containing vmem information.
                :start:     Amount of memory we start out using.
                :_data:     List of objects to be saved.
                :_pickles:  Number of pickles.
                :_epsilon:  Memory threshold.
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

        # Initialize the (private) internal `_data` collection as deques.
        # Fortunately, these are faster at adding/inserting/popping things. See
        # http://bit.ly/2MzkuMD for more details on this.
        self._data = deque()
        self._pickles = 1
        self._epsilon = epsilon

    @property
    def usage(self):
        """
            Readonly property that returns the percentage of memory used by this
            process.
        """
        current = ps.Process(os.getpid()).memory_info().rss
        return 100 * (current - self.start) / self.mem["available"]

    @property
    def available(self):
        """
            Readonly property that returns the current amount of available
            memory.
        """
        return ps.virtual_memory()[1]

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
            objects in `_pickles` to file. Returns None.

            Note that `obj` should be Pickleable, otherwise DataStore will throw
            a `pickle.PicklingError` error. Take a look here to find more info
            about object pickling: http://bit.ly/2yQV9ff.

                :obj:   (Pickleable) object added to _data.
        """
        # Check current data pressure.
        if self.usage > self._epsilon:
            self._pickle()
        
        self._data.append(obj)

    def _flush_data(self):
        """
            Flushes `._data`. Returns None.
        """
        self._data.clear()
    
    def _pickle(self):
        """
            Compresses the data in `_data` and adds the resulting picklestring
            object to `_pickles`. Also, as described below, we optimize the
            picklestring before adding it to `_pickles`. Finally, checks mem
            pressure to see whether we need to write any of the pickle objects
            to file.
        """
        # First, generate a picklestring. Then, using the `optmize()` method,
        # make the already small picklestring even smaller (see
        # http://bit.ly/2MDdGhh for more info on that). Then, write the baby
        # pickle to file and move on.
        picklestring = pkl.dumps(self._data)
        optimized_pickle = pklt.optimize(picklestring)

        # Write the picklestring to file and flush `_data`.
        self._pickle_to_file(optimized_pickle)
        self._flush_data()

    def _pickle_to_file(self, picklestring):
        """
            Write all the pickle data to a file. Returns None.
                :picklestring:  Optimized picklestring to be written to file.
        """
        # Write to the specified (internal, for now) path and make sure we're in
        # `wb` mode, as we're writing `bytes` objects to file.
        fname = "./hist/pickle{}.pkl".format(self._pickles)
        mode = "wb"

        with open(fname, mode) as pfile:
            pfile.write(picklestring)

        # If no exceptions are raised, then all is well! Increment the number of
        # pickles, and we're done.
        self._pickles += 1


if __name__ == "__main__":
    ds = DataStore()

    for i in range(0, 2**20):
        ds.add(i)
        print(ds.usage)

"""
    Then, for large numbers of iterations, we can write (or stream) the data to
    separate files and map the data to bins in each file. If we have n files and
    want to map into k bins, then we have n*k total bins; then, we simply have
    to reduce all n*k bins to k bins.
"""
