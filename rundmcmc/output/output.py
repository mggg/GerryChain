from collections import Counter
import json
import math

from rundmcmc.scores import efficiency_gap, mean_median, mean_thirdian


def p_value_report(score_name, ensemble_scores, initial_plan_score):
    """
    p_value_report takes an iterable :ensemble_scores: (scores computed on the
    ensemble seen in the random walk) and the :initial_plan_score: and returns
    a report like page 5 of Moon's PA analysis, including the fraction of plans
    in the ensemble that scored higher than the initial score and the p-value
    that the plan is chosen randomly as determined by the 'square root of
    2*epsilon' theorem.
    """
    count_higher = Counter(score >= initial_plan_score for score in ensemble_scores)
    total_scores = sum(count_higher.values())
    fraction_as_high = count_higher[True] / total_scores
    fraction_lower = count_higher[False] / total_scores

    # By Chikina-Frieze-Pegden, if a plan scores in the highest fraction_higher of all
    # plans seen in a random walk, then it has less than sqrt(2 * fraction_higher)
    # probability of being chosen randomly from the sample space. (Paraphrasing Moon's
    # PA report).

    p_value = math.sqrt(2 * fraction_as_high)
    opposite_p_value = math.sqrt(2 * fraction_lower)

    report = {'name': score_name,
              'initial_plan_score': initial_plan_score,
              'fraction_as_high': fraction_as_high,
              'p_value': p_value,
              'opposite_p_value': opposite_p_value}
    return report


class SlimPValueReport:
    scores = {
        "Efficiency Gap": efficiency_gap,
        "Mean-Median": mean_median,
        "Mean-Thirdian": mean_thirdian
    }

    def __init__(self, election, function=lambda epsilon: math.sqrt(2 * epsilon)):
        self.election = election
        self.counters = {name: Counter() for name in self.scores}
        self.initial_scores = None
        self.function = function

    def __call__(self, partition):
        election_results = partition[self.election.alias]

        if self.initial_scores is None:
            self.initial_scores = {name: score(election_results)
                                   for name, score in self.scores.items()}

        for name, score in self.scores.items():
            value = score(election_results)
            self.counters[name].update([value >= self.initial_scores[name]])

    def render(self):
        return {"election": self.election.name,
                "analysis": [self.render_score_analysis(score)
                            for score in self.scores]}

    def compute_p_value(self, score_name):
        return self.function(self.fraction_as_high(score_name))

    def compute_opposite_p_value(self, score_name):
        return self.function(self.fraction_as_low(score_name))

    def fraction_as_high(self, score_name):
        size_of_ensemble = sum(self.counters[score_name].values())
        if size_of_ensemble == 0:
            return math.nan
        number_as_high = self.counters[score_name][True]
        return number_as_high / size_of_ensemble

    def fraction_as_low(self, score_name):
        size_of_ensemble = sum(self.counters[score_name].values())
        if size_of_ensemble == 0:
            return math.nan
        number_as_low = 1 + self.counters[score_name][False]
        return number_as_low / size_of_ensemble

    def render_score_analysis(self, score):
        first_party, *others = self.election.parties_to_columns
        party_name = format_party_name(first_party)
        return {"score": score,
                "interpretation": "Positive values mean an advantage for {}".format(party_name),
                "fraction_as_high_as_original": self.fraction_as_high(score),
                "number_as_high_as_original": self.counters[score][True],
                "number_lower_than_original": self.counters[score][False],
                "p": self.compute_p_value(score)}

    def __str__(self):
        return json.dumps(self.render(), indent=2)


def format_party_name(name):
    if name.lower()[:-5] == "party":
        return name
    return "{} Party".format(name)


class Histogram:
    """
    A histogram with fixed bins, determined by the number of bins and the
    bounds for values.

    Anthony is working on the super smart histogram that does the binning for you.
    """

    def __init__(self, bounds, number_of_bins):
        self.bounds = bounds
        self.number_of_bins = number_of_bins

        left, right = bounds
        self.bin_size = (right - left) / number_of_bins

        self.bins = self.generate_bins()
        self.counter = Counter()

    def record(self, value):
        """
        :value: value to record in the histogram
        """
        return self.counter.update(self.find_bin(value))

    def find_bin_index(self, value):
        """
        find_bin conducts a binary search to find the right bin for the given value.
        """
        left = self.bounds[0]
        return math.floor((value - left) / self.bin_size)

    def find_bin(self, value):
        return self.bins[self.find_bin_index(value)]

    def generate_bins(self):
        left = self.bounds[0]
        for n in range(self.number_of_bins):
            yield (left + n * self.bin_size, left + (n + 1) * self.bin_size)

    def csv(self):
        header = "left,right,count\n"
        rows = ",".join((left, right, count) for (left, right), count in self.counter.items())
        body = "\n".join(rows)
        return header + body

    def json(self):
        return [[[left, right], count] for (left, right), count in self.counter.items()]


class ChainOutputTable:
    def __init__(self, data=None):
        if not data:
            data = list()
        self.data = data

    def append(self, row):
        self.data.append(row)

    def to_json(self, filename=None):
        if filename is None:
            return json.dumps(self.data)

        with open(filename, "w") as f:
            json.dump(self.data, f)

    # def to_dataframe(self):
    #     return pd.DataFrame(self.data)

    def __iter__(self):
        return self

    def __next__(self):
        return self.data

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.data[key]
        else:
            return [row[key] for row in self.data]

    def district(self, district_id):
        return get_from_each(self.data, district_id)


def get_chain_scores(chain, handlers):
    """Yield scores from handlers on each state in the chain.

    :chain: :class:`rundmcmc.chain.MarkovChain` instance.
    :handlers: Dictionary of {name: func} pairs.
    :returns: A generator yielding dictionaries of {name: result} pairs from
              handlers.

    """
    return ({key: handler(state) for key, handler in handlers.items()}
            for state in chain)


def handle_scores_separately(chain, handlers):
    table = ChainOutputTable()

    initialScores = {key: handler(chain.state) for
            key, handler in handlers.items() if key != "flips"}
    table.append(initialScores)

    nhandlers = {key: value for key, value in handlers.items() if key != "flips"}

    jsonToText = '{'
    jsonSave = False
    if "flips" in list(handlers.keys()):
        jsonToText += '"0": ' + json.dumps(handlers['flips'](chain.state))
        jsonSave = True

    for row in get_chain_scores(chain, nhandlers):
        table.append(row)
        if jsonSave:
            jsonToText += ", " + "\"" + str(chain.counter + 1) + "\""
            + ": " + json.dumps(handlers["flips"](chain.state))
    jsonToText += '}'

    return (table, jsonToText, nhandlers)


def get_from_each(table, key):
    return [{header: row[header][key] for header in row if key in row[header]}
            for row in table]


def log_dict_as_json(hist, scores, outputFile="output.json"):
    print(outputFile)
    if outputFile is not None:
        with open(outputFile, "w") as f:
            f.write(json.dumps(hist))


def flips_to_pngs(hist, scores, outputFile="output.png"):
    pass


def log_table_to_file(table, scores, outputFile="output.txt"):
    if outputFile:
        with open(outputFile, 'w') as f:
            for key in scores:
                if table[key] is not None:
                    f.write(", ".join([str(x) for x in table[key]]))
                    f.write("\n")


def pipe_to_table(chain, handlers, display=True, number_to_display=10,
                  bin_interval=1):
    table = ChainOutputTable()

    if number_to_display > 0:
        display_interval = math.floor(len(chain) / number_to_display)
    else:
        display_interval = 1

    counter = 0
    for row in handle_chain(chain, handlers):
        if display and counter % display_interval == 0:
            print("Step {}".format(counter))
            print(row)
        if counter % bin_interval == 0:
            table.append(row)
        counter += 1
    return table


def handle_chain(chain, handlers):
    for state in chain:
        yield {key: handler(state) for key, handler in handlers.items()}
