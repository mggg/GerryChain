"""
grid.py - create a small grid-graph example for the chain.
"""

from rundmcmc.validity import Validator, single_flip_contiguous
from rundmcmc.proposals import propose_random_flip
from rundmcmc.accept import always_accept
from rundmcmc.chain import MarkovChain
from rundmcmc.defaults.grid import Grid
import matplotlib.pyplot as plt

is_valid = Validator([single_flip_contiguous])

# Make a 20x20 grid
grid = Grid((20, 20))

chain = MarkovChain(propose_random_flip, is_valid, always_accept, grid, total_steps=5000)

pops = []
for partition in chain:
    # Grab the 0th districts population.
    pops.append(partition["population"][0])
    print(partition)

plt.style.use("ggplot")
plt.hist(pops)
plt.title("Population of district 0 over time")
plt.xlabel("Population")
plt.ylabel("Frequency")
plt.show()
