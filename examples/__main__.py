import sys
from rundmcmc.gui import read_basic_config


def main(args=None):
    if not args:
        args = sys.argv
    if len(args) < 1:
        raise ValueError("no config file provided")

    chain, chain_func, scores, output_func, output_type = read_basic_config(args[1])
    print("setup the chain")

    output = chain_func(chain)
    print("ran the chain")

    output_func(output, scores, output_type)


if __name__ == "__main__":
    main(sys.argv)
