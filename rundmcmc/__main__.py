from rundmcmc.defaults import BasicChain, example_partition
from rundmcmc.scores import mean_median, mean_thirdian, get_dict_of_flips, p_value


def print_summary(partition, scores):
    print("")
    print(f"Polsby-Popper: {partition['polsby_popper']}")


def main():
    initial_partition = PA_partition()

    chain = BasicChain(initial_partition, total_steps=10)

    scores = {
        'Mean-Median': mean_median,
        'Mean-Thirdian': mean_thirdian
    }

    for partition in chain:
        print_summary(partition, scores)
        print(chain.counter)
    get_dict_of_flips(chain)
    p_value(chain)


if __name__ == "__main__":
    main()
