# Reproducibility

If you've used GerryChain to do some analysis or research, you may want to ensure that
your analysis is completely repeatable by anyone else on their own computer. This guide
will walk you through the steps required to make that possible.

## Seed the random number generator

Each `MarkovChain` owns an independent random number generator, so making a chain reproducible
just requires passing a seed to the chain:

<!-- docs-test: skip -- fragment; references chain components defined nowhere on this page -->

```python
chain = MarkovChain(
    proposal, constraints, accept, initial_partition, total_steps, rng=2024
)
```

When randomness is needed before the chain, create one `random.Random` and pass it to the two
ownership boundaries:

<!-- docs-test: skip -- fragment; the literal `...` placeholders are not runnable -->

```python
import random

rng = random.Random(2024)
initial_partition = Partition.from_random_assignment(..., rng=rng)
chain = MarkovChain(..., initial_partition=initial_partition, rng=rng)
```

The chain passes its RNG to proposals, acceptance functions, and tree algorithms. Interleaved
chains therefore keep separate streams, which is mainly relevant for custom parallel-tempering
chains.

An integer seed starts a new stream each time a standalone function is called. For a sequence of
standalone operations (creating an initial partition followed by running a chain), create one
`random.Random(seed)` and pass that same instance to every call.

Chain trajectories do not depend on the `PYTHONHASHSEED` environment variable; older versions
of GerryChain required pinning it, but that is no longer necessary.

## Share your code on GitHub

Before anyone can run your code, they'll need to find it. We strongly recommend
publishing your source code as a [GitHub](https://github.com/) repository, and not as a `.zip` file on
your personal website. GitHub has a [desktop client](https://desktop.github.com/) that makes this easy, or you
can easily upload and edit your files on the website directly.

## Make your chains replayable

To save every plan from a chain without producing a large JSONL file, use
[Binary Ensemble]. Its `.bendl` format keeps the compressed assignment stream, dual
graph, and metadata together in one file. Install its Python package with:

```console
pip install binary-ensemble
```

Create an encoder, store the graph, and write each partition in that graph's node order.
Using `sort=None` preserves the order of the graph on which the chain is already running:

<!-- docs-test: skip -- fragment; requires binary-ensemble and a configured chain -->

```python
from binary_ensemble import BendlEncoder

encoder = BendlEncoder("saved-run.bendl", overwrite=True)
stored_graph = encoder.add_graph(initial_partition.graph, sort=None)
node_order = list(stored_graph.nodes)
encoder.add_metadata({"sampler": "ReCom", "seed": 2024})

with encoder.ben_stream() as ensemble:
    for partition in chain:
        assignment = partition.assignment.to_series().loc[node_order]
        ensemble.write(assignment.astype(int).tolist())
```

To replay the saved plans as GerryChain partitions, read the embedded graph and rebuild a
partition for each assignment. Updaters are recomputed as the file is streamed:

<!-- docs-test: skip -- fragment; requires binary-ensemble and application-specific updaters -->

```python
import pandas as pd

from binary_ensemble import BendlDecoder
from gerrychain import Partition

decoder = BendlDecoder("saved-run.bendl")
graph = decoder.read_graph()
node_order = pd.Index(graph.nodes)

for assignment in decoder:
    partition = Partition(
        graph,
        assignment=pd.Series(assignment, index=node_order),
        updaters=my_updaters,
    )
    # Analyze the replayed partition here.
```

Each decoded assignment is lossless and appears in the same sequence as the recorded
chain. The bundle also preserves the graph order needed to interpret those assignments.
See the Binary Ensemble guide to
[compressing a GerryChain run](https://binary-ensemble.readthedocs.io/en/latest/quick-help/compress-gerrychain-run/)
for graph reordering, encoding variants, and archival compression.

[Binary Ensemble]: https://binary-ensemble.readthedocs.io/

## Use the same versions of all of your dependencies

You will want to make sure that anyone who tries to repeat your analysis by
running your code will have the exact same versions of all of the software and packages
that you use, including the same version of Python.

The best way to do this is to create a {ref}`virtual environment <virtual-envs>`
and then save all of the dependencies to a file. This will allow anyone to recreate the
exact same environment that you used to run your code. To save the packages that are in
your current virtual environment, simply run

```console
pip freeze > requirements.txt
```

and this will save the versions of all of your packages to a file called
`requirements.txt`. You can then share this file with anyone who wants to run your code,
and they can create the same virtual environment by running

```console
pip install -r requirements.txt
```
