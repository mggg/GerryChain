from rundmcmc.defaults import BasicChain, PA_partition
from rundmcmc.scores import compute_meta_graph_degree


def main():
    initial_partition = PA_partition()
    chain = BasicChain(initial_partition, total_steps=25)

    compute_meta_graph_degree(chain)


if __name__ == '__main__':
    main()
