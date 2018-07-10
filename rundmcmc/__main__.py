import sys
from rundmcmc.parse_config import read_basic_config
import glob
import zipfile
import os

def main(args=None):
    if not args:
        args = sys.argv
    if len(args) < 1:
        raise ValueError("no config file provided")

    chain, chain_func, scores, output_func, output_type = read_basic_config('gui_test.ini')
    print("setup the chain")

    output = chain_func(chain)
    print("ran the chain")

    output_func(output, scores, output_type)
C:\\

if __name__ == "__main__":
    main(sys.argv)
    name = glob.glob("/tmp/chains/*")[0].split('/')[2].split('.')[0]
    file_list = glob.glob("/tmp/chains/*")
    print(file_list)
    with zipfile.ZipFile("/tmp/chains/" + name + '.zip', 'w') as myzip:
      for f in file_list:
        myzip.write(f)
