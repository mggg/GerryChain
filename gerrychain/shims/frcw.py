from .serialize import serialize_partition

from typing import List
import random
import secrets
import functools
import pcompress
import gerrychain
import tempfile
import subprocess


def frcw_recom(
    partition: gerrychain.Partition,
    pop_col: str,
    pop_target: float,
    pop_tol: float,
    steps: int,
    executable: str = "frcw",
    variant: str = "district-pairs-rmst",
    n_threads: int = 2,
    batch_size: int = 2,
    extra_args: List[str] = []
):
    random_prefix = secrets.token_hex(8)
    with tempfile.TemporaryDirectory() as dirname:
        graph_json_path = f"{dirname}/dual_graph.json"
        chain_path = f"{dirname}/{random_prefix}pcompress.chain"
        serialize_partition(partition, graph_json_path)
        serialize_partition(partition, "dual_graph.json")
        command = [
            executable,
            "--graph-json",
            graph_json_path,
            "--assignment-col",
            "assignment",
            "--n-steps",
            str(steps),
            "--n-threads",
            str(n_threads),
            "--pop-col",
            pop_col,
            "--tol",
            str(pop_tol),
            "--variant",
            variant,
            "--writer",
            "pcompress",
            "--batch-size",
            str(batch_size),
            "--rng-seed",
            str(random.randint(0, 10000)),  # raise UserWarning
        ]
        command.extend(extra_args)
        command.extend([
            "|",
            "xz",
            ">",
            chain_path,
        ])
        print(" ".join(command)) # debug
        subprocess.run(" ".join(command), shell=True)

        for chain in pcompress.Replay(
            partition.graph, chain_path, updaters=partition.updaters
        ):
            yield chain


def frcw_reversible_recom(
    partition: gerrychain.Partition,
    pop_col: str,
    pop_target: float,
    pop_tol: float,
    steps: int,
    M: int = 30,
    executable: str = "frcw",
):
    return frcw_recom(partition, pop_col, pop_target, pop_tol, steps, executable=executable, variant="reversible", extra_args = ["--balance-ub", str(M)])
