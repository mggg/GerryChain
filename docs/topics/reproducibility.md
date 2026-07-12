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
chain = MarkovChain(..., initial_state=initial_partition, rng=rng)
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

## Make your chains speedily replayable

It is sometimes desirable to allow others to reproduce or "replay" your chain runs step
by step. In such cirucmstances, we recommend using [pcompress](https://github.com/mggg/pcompress) which efficiently and
rapidly stores your MCMC chain runs in a highly-compressed format. It can then be
quickly read-in by `pcompress` at a later date. To setup [pcompress](https://github.com/mggg/pcompress), you need to first
[install Cargo](https://doc.rust-lang.org/cargo/getting-started/installation.html). Then, you can install [pcompress](https://github.com/mggg/pcompress) by installing running `cargo
install pcompress` and `pip install pcompress` in your terminal.

To use [pcompress](https://github.com/mggg/pcompress), you can wrap your `MarkovChain` instances with `Record` and
pass along the file name you want to save your chain as. For example, this will save
your chain run as `saved-run.chain`:

<!-- docs-test: skip -- incomplete fragment; requires the optional pcompress package -->

```python
from gerrychain import MarkovChain
from pcompress import Record

chain = MarkovChain(
    # chain setup here
)

for partition in Record(chain, "saved-run.chain"):
    # normal chain stuff here
```

Then, if you want to replay your chain run, you can select the same filename and pass
along the graph that was used to generate the chain, along with any updaters that are needed:

<!-- docs-test: skip -- incomplete fragment; requires the optional pcompress package -->

```python
from pcompress import Replay

for partition in Replay(graph, "saved-run.chain", updaters=my_updaters):
    # normal chain stuff here
```

The two code samples provided will produce totally equivalent chain runs, up to
reordering. Each step in the replayed chain run will match each step in the recorded
chain run. Furthermore, the replay process will be faster than the original chain
running process and is compatible across future and past releases of GerryChain.

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
