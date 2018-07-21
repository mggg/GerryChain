import os

import matplotlib.pyplot as plt

from rundmcmc.defaults.grid import Grid, grid_size

from rundmcmc.validity import (fast_connected, Validator, no_vanishing_districts,
                               within_percent_of_ideal_population)

from rundmcmc.proposals import reversible_chunk_flip

from rundmcmc.accept import always_accept

from rundmcmc.chain import MarkovChain


# Makes a simple grid and runs the MCMC. Mostly for testing proposals

grid = Grid((20, 20))  # was (4,4)

pop_limit = .3
population_constraint = within_percent_of_ideal_population(grid, pop_limit)

grid_validator2 = Validator([fast_connected, no_vanishing_districts,
                             population_constraint])

grid_validator = Validator([fast_connected, no_vanishing_districts, grid_size])

dumb_validator = Validator([fast_connected, no_vanishing_districts])


chain = MarkovChain(reversible_chunk_flip, grid_validator2, always_accept,
                    grid, total_steps=100)

# Outputs .pngs for animating
newdir = "./Outputs/Grid_Plots/"
os.makedirs(os.path.dirname(newdir + "init.txt"), exist_ok=True)
with open(newdir + "init.txt", "w") as f:
    f.write("Created Folder")

i = 1
for partition in chain:
    plt.matshow(partition.as_list_of_lists())
    plt.savefig(newdir + "g3_%04d.png" % i)
    plt.close()
    i += 1

# To animate:
# ffmpeg -framerate 5 -i g3_%04d.png -c:v libx264
# -profile:v high -crf 20 -pix_fmt yuv420p grid3.mp4
