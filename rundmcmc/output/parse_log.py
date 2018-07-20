from collections import Counter
import matplotlib.pyplot as plt
import numpy as np
import re

log_name = "template.log"

regex = re.compile("constraint failed: (.*)")

fails = []
with open(log_name) as f:
    for line in f:
        match = regex.search(line.strip())

        if match:
            fails.append(match.group(1))

counter = Counter(fails)

labels, values = zip(*counter.items())
indexes = np.arange(len(labels))
width = 1

plt.style.use("ggplot")
plt.bar(indexes, values, width)
plt.xticks(indexes, labels)
plt.show()
