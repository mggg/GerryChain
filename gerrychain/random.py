import os
import random

seed = os.environ.get("GERRYCHAIN_RANDOM_SEED", 2018)
random.seed(seed)
