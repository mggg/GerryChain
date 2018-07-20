
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


def flips_to_dict(chain, handlers=None):
    hist = {0: chain.state.assignment}
    for state in chain:
        hist[chain.counter + 1] = state.flips
    return hist
