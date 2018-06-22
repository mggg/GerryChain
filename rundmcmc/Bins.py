
import psutil as ps


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
        self.mem = ps.virtual_memory()
        self.total_memory = self.mem[0]
        self.raw_available_memory = self.mem[1]
        self.percent_available_memory = self.mem[2]
    

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
"""