import matplotlib.pyplot as plt


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
    _, axes = plt.subplots(nrows=numrows, ncols=numcols)

    if numcols == 1:
        quadrants = {key: i for i, key in enumerate(scores.keys())}
    else:
        quadrants = {
            key: (i % numcols, int(i / numcols))
            for i, key in enumerate(scores.keys()) if i < numrows * numcols
        }

    initial_scores = table[0]

    for i, key in enumerate(scores.keys()):
        if i < numrows * numcols:
            quadrant = quadrants[key]
            axes[quadrant].hist(table[key], bins=50)
            axes[quadrant].set_title(key)
            axes[quadrant].axvline(x=initial_scores[key], color='r')
    if outputFile:
        plt.savefig(outputFile)
    else:
        plt.show()
