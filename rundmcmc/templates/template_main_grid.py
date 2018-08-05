import os

import matplotlib.pyplot as plt

from rundmcmc.defaults.grid import Grid, grid_size

from rundmcmc.validity import (fast_connected, single_flip_contiguous,
                               Validator, no_vanishing_districts,
                               within_percent_of_ideal_population)

from rundmcmc.proposals import propose_random_flip_no_loops

from rundmcmc.accept import always_accept

from rundmcmc.chain import MarkovChain


# Makes a simple grid and runs the MCMC. Mostly for testing proposals

grid = Grid((5, 5), with_diagonals=False)  # was (4,4)


def perimeter_constraint(grid, threshold=10):
    return all(perimeter <= threshold for perimeter in grid['perimeters'].values())


pop_limit = .3
population_constraint = within_percent_of_ideal_population(grid, pop_limit)

grid_validator2 = Validator([single_flip_contiguous, no_vanishing_districts,
                             population_constraint, perimeter_constraint])

grid_validator = Validator([fast_connected, no_vanishing_districts, grid_size])

dumb_validator = Validator([fast_connected, no_vanishing_districts])


chain = MarkovChain(propose_random_flip_no_loops, grid_validator2, always_accept,
                    grid, total_steps=1000)

# Outputs .pngs for animating
newdir = "./Outputs/Grid_Plots/"
os.makedirs(os.path.dirname(newdir + "init.txt"), exist_ok=True)
with open(newdir + "init.txt", "w") as f:
    f.write("Created Folder")

counter = 0
for partition in chain:
    plt.matshow(partition.as_list_of_lists())
    plt.savefig(newdir + "g3_%04d.png" % counter)
    plt.close()
    counter += 1
    print(partition['perimeters'])

# To animate:
# ffmpeg -framerate 5 -i g3_%04d.png -c:v libx264
# -profile:v high -crf 20 -pix_fmt yuv420p grid3.mp4
