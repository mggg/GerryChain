import math
import tqdm
from gerrychain.proposals import reversible_recom


def cfp_significance(partition, pop_col, pop_tol, labeler, trajectory_length = 100000, M=30):
    """
    Calculuates the significance of the given partition, with the given lableler and trajectory_length, as described in https://doi.org/10.1073/PNAS.1617540114 using reversible ReCom.
    """
    ideal_pop = sum(partition[pop_col].values()) / len(partition)
    sigmas = [labeler(partition)]

    current_partition = partition
    for _ in tqdm.tqdm(range(trajectory_length)):
        current_partition = reversible_recom(current_partition, pop_col, ideal_pop, pop_tol, M=M)
        sigmas.append(float(labeler(current_partition)))
    
    smaller_than = len([x for x in sigmas if x <= sigmas[0]])
    # epsilon = smaller_than / (len(sigmas) + 1)
    epsilon = smaller_than / len(sigmas) # if typo
    significance = math.sqrt(2*epsilon)

    return min(1, significance)
