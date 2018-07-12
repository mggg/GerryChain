import json
import math
from rundmcmc.output import ChainOutputTable


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


class PeriodicFlipsReport:
    def __init__(self, cadence=100):
        self.cadence = cadence
        self.counter = 0

    def __call__(self, partition):
        if self.counter % self.cadence == 0:
            # Then we just returned a report, so we'll reset flips_since_last_report
            self.flips_since_last_report = dict()

        self.counter += 1

        if partition.flips:
            self.flips_since_last_report = {**self.flips_since_last_report, **partition.flips}

        if self.counter % self.cadence == 0:
            return self.flips_since_last_report
        else:
            return None


def handle_chain(chain, handlers):
    for state in chain:
        yield {key: handler(state) for key, handler in handlers.items()}


def pipe_to_table(chain, handlers, display=True, display_frequency=100,
                  bin_frequency=1):
    table = ChainOutputTable()
    display_interval = math.floor(len(chain) / display_frequency)
    counter = 0
    for row in handle_chain(chain, handlers):
        if counter % display_interval == 0:
            if display:
                print(f"Step {counter}")
                print(row)
        if counter % bin_frequency == 0:
            table.append(row)
        counter += 1
    return table


def flips_to_dict(chain, handlers=None):
    hist = {0: chain.state.assignment}
    for state in chain:
        hist[chain.counter + 1] = state.flips
    return hist


def handle_scores_separately(chain, handlers):
    table = ChainOutputTable()

    initialScores = {key: handler(chain.state) for
            key, handler in handlers.items() if key != "flips"}
    table.append(initialScores)

    nhandlers = {key: value for key, value in handlers.items() if key != "flips"}

    jsonToText = '{'
    jsonSave = False
    if "flips" in list(handlers.keys()):
        jsonToText += '{0: ' + json.dumps(handlers['flips'](chain.state)) + '}'
        jsonSave = True

    for row in handle_chain(chain, nhandlers):
        table.append(row)
        if jsonSave:
            jsonToText += "{" + str(chain.counter + 1) \
            + ":" + json.dumps(handlers["flips"](chain.state)) + "}"
    jsonToText += '}'

    return (table, jsonToText, nhandlers)
