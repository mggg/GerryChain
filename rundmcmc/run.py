
def run(chain, loggers):
    """run runs the chain.
    All the `during` methods of each of the loggers are called for each step
    in the chain. The `before` and `during` methods each take a `state` parameter,
    which is an instance of the Partition class. After the random walk is
    over, we call the `after` method of each logger for clean-up tasks, like
    printing a summary or generating figures.

    :chain: MarkovChain instance
    :loggers: list of Loggers (objects with before, during, and after methods)
    """

    for logger in loggers:
        logger.before(chain)

    for state in chain:
        for logger in loggers:
            logger.during(state)

    return [logger.after(chain.state) for logger in loggers]
