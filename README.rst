===============================
RunDMCMC
===============================


.. image:: https://circleci.com/gh/gerrymandr/RunDMCMC.svg?style=svg
    :target: https://circleci.com/gh/gerrymandr/RunDMCMC
.. image:: https://codecov.io/gh/gerrymandr/RunDMCMC/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/gerrymandr/RunDMCMC
.. image:: https://api.codacy.com/project/badge/Grade/b02dfe3d778b40f3890d228889feee52
   :target: https://www.codacy.com/app/msarahan/RunDMCMC?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=gerrymandr/RunDMCMC&amp;utm_campaign=Badge_Grade
.. image:: https://readthedocs.org/projects/rundmcmc/badge/?version=latest
   :target: https://rundmcmc.readthedocs.io/en/latest
   :alt: Documentation Status


This code implements Monte-Carlo exploration of districting plans, exploring
the space around an initial districting plan to give some idea of the degree of
gerrymandering. It is a Python rewrite of the chain C++ program
(https://github.com/gerrymandr/cfp_mcmc), originally by Maria Chikina, Alan
Frieze and Wesley Pegden, for their paper, "Assessing significance in a Markov
chain without mixing" (http://www.pnas.org/content/114/11/2860)


Installation
============

Ideally, the following conda command will work:

``conda install -c gerrymandr rundmcmc``

Should our release system be broken, cloning this repository and manually
running ``setup.py`` will also work::

    git clone https://github.com/gerrymandr/RunDMCMC.git
    cd RunDMCMC
    python3 setup.py install


Example usage
=============

Below is an example of using the chain. It uses the ``v0.1.0`` release, which
is rough around the edges, but usable.

.. code-block:: python

    import json

    import geopandas as gp
    import networkx.readwrite

    from rundmcmc.defaults import BasicChain
    from rundmcmc.make_graph import add_data_to_graph, get_assignment_dict
    from rundmcmc.partition import Partition
    from rundmcmc.scores import (efficiency_gap, final_report, mean_median,
                                mean_thirdian)
    from rundmcmc.updaters import cut_edges, votes_updaters


    def example_partition():
        df = gp.read_file("./testData/mo_cleaned_vtds.shp")

        with open("./testData/MO_graph.json") as f:
            graph_json = json.load(f)

        graph = networkx.readwrite.json_graph.adjacency_graph(graph_json)

        assignment = get_assignment_dict(df, "GEOID10", "CD")

        add_data_to_graph(df, graph, ['PR_DV08', 'PR_RV08'], id_col='GEOID10')

        updaters = {
            **votes_updaters(['PR_DV08', 'PR_RV08'], election_name='08'),
            'cut_edges': cut_edges
        }
        return Partition(graph, assignment, updaters)
    

    def print_summary(partition, scores):
        print("")
        for name, score in scores.items():
            print(f"{name}: {score(partition, 'PR_DV08%')}")


    def main():
        initial_partition = example_partition()

        chain = BasicChain(initial_partition, total_steps=100)

        scores = {
            'Efficiency Gap': efficiency_gap,
            'Mean-Median': mean_median,
            'Mean-Thirdian': mean_thirdian
        }

        for partition in chain:
            print_summary(partition, scores)


    if __name__ == "__main__":
        main()
