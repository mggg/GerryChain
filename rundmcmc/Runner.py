
from rundmcmc.Loggers import Loggers


class Runner:
    def __init__(self, Chain, funcs=None, ends=None, **kwargs):
        """
            Runner is a wrapper for the MarkovChain class that tracks
            statistics as we move through the states of the chain. Uses
            regular Python lists for performance (as it's faster to append
            to a linked list than it is to merge two NumPy arrays).
            :Chain:     Instance of the MarkovChain class.
            :funcs:     List of functions that log data while the chain runs.
            :ends:      List of functions that log/save/do whatever with data
                        after the chain completes.
            :**kwargs:  Command-line (or extraneous) arguments.
        """
        self.Chain = Chain
        self.Loggers = Loggers(funcs, ends)

        # Set default interval (or take it from additional keyword arguments),
        # but don't use a ternary logic operator here bc the line would be
        # too long. Then, if Loggers exist, set the interval to the default
        # binning rate (1%).
        self.interval = None

        if kwargs.get("interval") is None:
            self.interval = max(1, int(self.Chain.total_steps * 0.01))
        else:
            self.interval = max(1, int(kwargs["interval"]))

        # Find the total number of districts.
        stats = self.Chain.state
        first_key = next(iter(stats.keys()))
        self.num_districts = len(stats[first_key])

        # Initialize histogram, generating lists at each key.
        self.histograms = {stat: list(cds.values()) for stat, cds in stats.items()}

        # Run the chain.
        self._run_chain()

    def _run_chain(self):
        """
            Class-private method that runs automagically. Runs the chain
            and, at the specified intervals, bins the current statistics
            of the partition. This can be augmented to log stats to the
            console at the same rate, but we can add that as a flag later.
            Futhermore, this should be modified to control for interval
            size, as small intervals with a large number of iterations will
            stress the memory of the machine. We should consider writing
            to a file (every n intervals) or using another caching method.
        """
        step = 0

        # Loop for running the chain. *This method needs to be augmented.*
        for state in self.Chain:
            # If we encounter an interval step, get the current statistics
            # and add their values to the existing histograms. Also passes
            # the current state to the Loggers object.
            if step % self.interval == 0:
                self.Loggers.during_chain(state)
                for stat in self.histograms:
                    self.histograms[stat] += list(state[stat].values())

            step += 1

        # Run all the functions designed for when the state has completed.
        self.Loggers.after_chain(state)
