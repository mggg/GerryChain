
import psutil as ps
import os
import sys
import shutil
import pickle as pkl
import pickletools as pklt
from collections import deque, OrderedDict


class DataStore:
    """
        The DataStore class stores data quickly and small-ly (if that's a word).
        Lightweight and easy to use, this is the perfect solution for users who
        need to store massive amounts of data efficiently (see running 2**31
        steps on the chain and storing every data point).
    """
    def __init__(self, data=None, epsilon=15):
        """
            Initialize.
                :data:      Initial data.
                :epsilon:   Default memory threshold that must be eclipsed before
                            pickling/filewriting.

            Properties.
                :_data:         Deque of objects to be saved.
                :_pickles:      OrderedDict. <k, v> pairs are such that k
                                represents the index of the last item added to
                                `_data` before pickling, where v is the file
                                `_data` was written to.
                :_epsilon:      Memory threshold.
                :_i:            Current place in iteration.
                :_cache:        File being used by the iterator.
                :_filenum:      Number of file being used by the iterator.
                :_lastindex:    Last index saved in file `_filecache`.
                :_runnning_i:   Current index on a loaded block of data.
        """
        # Initialize the (private) internal `_data` collection as deques.
        # Fortunately, these are faster at adding/inserting/popping things. See
        # http://bit.ly/2MzkuMD for more details on this.
        self._data = deque()
        self._pickles = OrderedDict()
        self._epsilon = epsilon

        # Create the directory to store histogram data.
        os.mkdir("./hist/")

        # Initialize the remaining properties.
        self._i = 0
        self._cache = None
        self._filenum = 0
        self._lastindex = 0
        self._running_i = 0

    @property
    def usage(self):
        """
            Readonly property that returns the percentage of memory used by this
            process.
        """
        current = sys.getsizeof(self._data)
        return 100 * (current / self.available)

    @property
    def available(self):
        """
            Readonly property that returns the current amount of available
            memory.
        """
        return ps.virtual_memory()[1]

    def add(self, obj=None):
        """
            Adds `obj` to the list of data. Also checks current memory
            pressure to see whether to pickle objects or write existing pickled
            objects in `_pickles` to file. Returns None.

            Note that `obj` should be Pickleable, otherwise DataStore will throw
            a `pickle.PicklingError` error. Take a look here to find more info
            about object pickling: http://bit.ly/2yQV9ff.

                :obj:   (Pickleable) object added to `_data`.
        """
        # Check to make sure that we aren't adding nothing.
        if obj is None:
            raise ReferenceError("Objects of type None cannot be stored.")
        # Check current data pressure.
        if self.usage > self._epsilon:
            self._pickle()

        self._data.append(obj)

    def append(self, obj):
        """
            Alias for `add()`.

                :obj: (Pickleable) object added to `_data`.
        """
        self.add(obj)

    def _flush_data(self):
        """
            Flushes `._data`. Returns None.
        """
        del self._data
        self._data = []

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
        fname = "./hist/pickle_{}.pkl".format(len(self._pickles))
        mode = "wb"

        with open(fname, mode) as pfile:
            pfile.write(picklestring)

        # After writing, add an additional key to `_pickles` containing the last
        # index added to `_data` before pickling. Accessing the last-added key
        # is O(1).
        files = len(self._pickles)
        last_current_index = len(self._data)

        if files < 1:
            self._pickles[last_current_index] = fname
        else:
            last_saved_index = next(reversed(self._pickles))
            self._pickles[last_saved_index + last_current_index] = fname

    def __len__(self):
        """
            Returns the number of pickled items plus the number of items held in
            memory. Called when len(DataStore) is called.
        """
        if len(self._pickles) == 0:
            return len(self._data)

        return len(self._data) + next(reversed(self._pickles))

    def __str__(self):
        return "DataStore object at {}\nMemory Usage: {}\nItems: {}\nFiles: {}" \
                .format(hex(id(self)), self.usage, len(self), len(self._pickles))

    def __getitem__(self, index):
        """
            Given an index, get the data. Uses a short, linear search over the
            keys of `_pickles` to find the correct file, then returns the data.

                :index: Index of data point to be retrieved.
        """
        stores = len(self._pickles)

        if stores == 0:
            return self._data[index]
        else:
            last_saved_index = next(reversed(self._pickles))

            # We have the last saved index. If the desired index is greater than
            # the one last saved, then we simply get the remainder of `index` /
            # `last_saved_index`. Otherwise, find the file that the entry at
            # index `index` is in, unpickle it, and retrieve the data point.
            if index > last_saved_index:
                return self._data[index % last_saved_index]
            else:
                indices = iter(self._pickles)

                for i in indices:
                    if index < i:
                        # We've found the right file! Now, we can just unpickle
                        # and return the entry. Also, if we want to find the
                        # `index`th entry in this file, we need to get the entry
                        # that's `i - index` spaces from the *end* of the list –
                        # i.e. the `index - i`th element (I'm being pythonic)!
                        unpkl = None
                        with open(self._pickles[i], "rb") as pfile:
                            unpkl = pkl.load(pfile)
                            return unpkl[index - i]

    def __iter__(self):
        """
            For iteration.
        """
        self.i = 0
        return self

    def __next__(self):
        """
            Called when the next(DataStore) method is called, typically in
            for loops. For the love of god do NOT call list() on this thing. I'll
            put a warning in here somewhere about that.

            Futhermore, we expressly don't want to use the simple __getitem__
            method here, as it'd require a completely unnecessary amount of
            filereads and would take forever.

            TODO Warn people against calling list() on this, as it'll destroy
            their computer (probably). I'll put something like "Are you sure you
            want to expand this object to a list? It will take up <size>gb on your
            system uncompressed."
        """
        if self.i < len(self):
            # If we have no files.
            if len(self._pickles) == 0:
                result = self._data[self.i]
                self.i += 1
                return result

            # If we have some files, we need to iterate over them progressively.
            elif len(self._pickles) is not 0:
                indices = list(self._pickles)

                # If we have no file loaded, load the first one. Alternatively,
                # we load the next file. Finally, if we need to start iterating
                # over things currently held in memory, dump the file reference
                # and set `_cache` to point to `_data`.
                if self._cache is None:
                    filename = self._pickles[indices[self._filenum]]
                    with open(filename, "rb") as pfile:
                        self._cache = pkl.load(pfile)

                elif self._running_i == len(self._cache) and self._filenum + 1 < len(indices):
                    self._filenum += 1
                    filename = self._pickles[indices[self._filenum]]

                    with open(filename, "rb") as pfile:
                        self._cache = pkl.load(pfile)

                    # Reset our running iteration counter.
                    self._running_i = 0

                elif self._running_i == len(self._cache) and self._filenum + 1 == len(indices):
                    # Point `_cache` to `_data`, and reset our running iteration counter.
                    self._cache = self._data
                    self._running_i = 0

                result = self._cache[self._running_i]
                self.i += 1
                self._running_i += 1
                return result
        else:
            # Done!
            raise StopIteration

    def __del__(self):
        """
            Called when an instance of this class is destroyed. Returns None.
        """
        shutil.rmtree("./hist/")


if __name__ == "__main__":
    ds = DataStore(epsilon=0.1)

    for i in range(0, 2**20):
        ds.add(i)

        if i % 10000 == 0:
            print("Step {}".format(i))
            print(ds)
            print()

    for i in ds:
        print(i)
