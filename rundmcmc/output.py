import json
import matplotlib.pyplot as plt


class ChainOutputTable:
    def __init__(self, data=None):
        if not data:
            data = list()
        self.data = data

    def append(self, row):
        self.data.append(row)

    def json(self, row):
        return json.dumps(self.data)

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


def get_from_each(table, key):
    return [{header: row[header][key] for header in row if key in row[header]}
            for row in table]


def hist_of_table_scores(table, scores=None, outputFile="output.png"):
    """Creates a histogram of each score in scores, where
    table is keyed on score and has values that can be binned

    outputs a window plot of histograms of logged scores
    """
    if not scores:
        scores = table.keys()
    numrows = min(2, len(scores))
    numcols = int(len(scores) / numrows)
    numrows = max(numrows, 1)
    numcols = max(numcols, 1)
    fig, axes = plt.subplots(ncols=numcols, nrows=numrows)

    scoreNames = [x for x in scores.keys()][: numrows * numcols]
    quadrants = {
        key: (int(i / numcols), i % numcols)
        for i, key in enumerate(scoreNames)
    }

    initial_scores = table[0]

    for key in scores:
        quadrant = quadrants[key]
        axes[quadrant].hist(table[key], bins=50)
        axes[quadrant].set_title(key)
        axes[quadrant].axvline(x=initial_scores[key], color='r')
    if outputFile:
        plt.savefig(outputFile)
    else:
        plt.show()


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
