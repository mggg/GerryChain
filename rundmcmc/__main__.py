from rundmcmc.parse_config import read_basic_config


def main():
    chain, chain_func, scores, output_func, output_type = read_basic_config("basic_config.ini")
    print("setup the chain")

    output = chain_func(chain)
    print("ran the chain")

    output_func(output, scores, output_type)


if __name__ == "__main__":
    main()
