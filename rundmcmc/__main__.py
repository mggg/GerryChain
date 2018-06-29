from rundmcmc.parse_config import read_basic_config


def main():
    chain, chain_func, scores, output_func = read_basic_config("basic_config.ini")
    print("setup the chain")

    output = chain_func(chain)
    print("ran the chain")

    output_func(output, scores)


if __name__ == "__main__":
    main()
