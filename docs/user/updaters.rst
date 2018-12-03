Updaters
========

Depending on the questions you are investigating, there are many different values you might want to
compute for each partition in your Markov chain. If you are interested in compactness, you might want
to compute the area and perimeter of each part of the partition so that you can compute compactness scores.
If you are interested in partisan lean, you might want to compute hypothetical election results
using the districts defined by the partition.

The GerryChain :class:`~gerrychain.Partition` allows you to pass in arbitrary "updater" functions for
each 