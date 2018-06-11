"""Implementation of random walk.  Get random numbers, do something with them.  Dispatch to metric
functions and record to histograms"""

try:
    # this is an optimization, perhaps premature.  mkl_random can be much faster for
    #    generating random numbers, but I'm not sure this will really be our slow spot.
    # https://software.intel.com/en-us/blogs/2016/06/15/faster-random-number-generation-in-intel-distribution-for-python
    import mkl_random as rnd
    SEED = 0
    PRNG_IMPL = 'SFMT19937'
    rnd.seed(SEED, PRNG_IMPL)
except ImportError:
    import numpy.random as rnd


def _buffer_choices(choices, buffer_size):
    """Generating random numbers one at a time is slow.
    If we buffer a million or so at a time, we can go faster."""
    return rnd.choice(choices, size=int(buffer_size))


def execute_walk(aggregate_state, steps, reporting_frequency=1E18, metrics=None,
                 buffer_size=1E6):
    # scientific notation is float, but we really want ints to be looping over
    reporting_frequency = int(reporting_frequency)
    steps = int(steps)

    choice_buffer = _buffer_choices(aggregate_state.graph_edges, buffer_size)
    buffer_count = 0

    for step in range(steps):
        try:
            choice = choice_buffer[step - buffer_size * buffer_count]
        except IndexError:
            choice_buffer = _buffer_choices(aggregate_state.graph_edges, buffer_size)
            buffer_count += 1
            choice = choice_buffer[step - buffer_size * buffer_count]
        aggregate_state.reassign_subunit(*choice)
        # compute metrics
