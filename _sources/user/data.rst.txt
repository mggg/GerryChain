===================
Good Data Practices
===================

Of course, in the process of working with ``gerrychain``, it is inevitable
that you will want to examine some data. While there are a lot of great
ways to store and deal with data, there are some ways that we have found
more helpful than others which we would like to share here.

.. attention::

    In general, the techniques described here are not appropriate
    for storing the entire Markov chain of redistricting plans. Instead, the
    methods described below are primarily aimed at the collection and analysis
    of statistical information about each of the partitions in the chain.
    
    In the event that you would like to store each partition in the chain in 
    its entirety, we would recommend that you make use of our 
    `PCompress <https://github.com/mggg/pcompress>`_ package.

Writing Data to JSONL
---------------------

.. raw:: html

    <div class="center-container">
      <a href="https://github.com/mggg/GerryChain/tree/main/docs/_static/PA_VTDs.json" class="download-badge" download>Download PA File</a>
    </div>
    <br style="line-height: 5px;">

One of the most common methods for storing data is to write the 
relevant information to a JSONL file. Here is an example with our
Pennsylvania data:

.. code-block:: python

    from gerrychain import Graph, Partition
    from gerrychain.updaters import Tally, cut_edges
    from gerrychain import MarkovChain
    from gerrychain.constraints import contiguous
    from gerrychain.proposals import recom
    from gerrychain.accept import always_accept
    from functools import partial

    import random
    random.seed(42)


    graph = Graph.from_json("./PA_VTDs.json")

    initial_partition = Partition(
        graph,
        assignment="2011_PLA_1",
        updaters={
            "population": Tally("TOT_POP", alias="population"),
            "area": Tally("area", alias="area"), # We can only do this since PA_VTDs.json 
                                                 # has an "area" attribute for each node 
            "cut_edges": cut_edges,
        }
    )

    ideal_population = sum(initial_partition["population"].values()) / len(initial_partition)

    proposal = partial(
        recom,
        pop_col="TOT_POP",
        pop_target=ideal_population,
        epsilon=0.01,
        node_repeats=2
    )

    chain = MarkovChain(
        proposal=proposal,
        constraints=[contiguous],
        accept=always_accept,
        initial_state=initial_partition,
        total_steps=20
    )

And now we can run the chain and write the data to a JSONL file:

.. code-block:: python

    import json

    with open("PA_output.jsonl", "w") as f:
        for i, partition in enumerate(chain):
            data = {
                "step": i,
                "populations": partition["population"],
                "areas": partition["area"],
                "n_cut_edges": len(partition["cut_edges"])  
            }
            # Add newline character to separate entries in JSONL file
            f.write(json.dumps(data) + "\n")  



This will produce output with lines of the form:

.. code-block:: console

    {"step": 0, "populations": {"3": 706653, "10": 706992, "9": 702500, "5": 695917, "15": 705549, "6": 705782, "11": 705115, "8": 705689, "4": 705669, "18": 705847, "12": 706232, "17": 699133, "7": 712463, "16": 699557, "14": 705526, "13": 705028, "2": 705689, "1": 705588}, "areas": {"3": 1.0871722918594986, "10": 2.367083752509999, "9": 1.579113333589498, "5": 3.0122633409220008, "15": 0.35732152655850036, "6": 0.23906899201449974, "11": 0.949621240640999, "8": 0.19927536179150002, "4": 0.4185125039540002, "18": 0.5691588362529991, "12": 0.6009789760809999, "17": 0.48479405839200057, "7": 0.23842544605850016, "16": 0.28336540997449977, "14": 0.06036624468650007, "13": 0.04260779136050022, "2": 0.02065452186049993, "1": 0.02454134236900001}, "n_cut_edges": 2361}

which is a bit easier to read with some formatting:

.. code-block:: json

    {
      "step": 0,
      "populations": {
        "3": 706653,
        "10": 706992,
        "9": 702500,
        "5": 695917,
        "15": 705549,
        "6": 705782,
        "11": 705115,
        "8": 705689,
        "4": 705669,
        "18": 705847,
        "12": 706232,
        "17": 699133,
        "7": 712463,
        "16": 699557,
        "14": 705526,
        "13": 705028,
        "2": 705689,
        "1": 705588
      },
      "areas": {
        "3": 1.0871722918594986,
        "10": 2.367083752509999,
        "9": 1.579113333589498,
        "5": 3.0122633409220008,
        "15": 0.35732152655850036,
        "6": 0.23906899201449974,
        "11": 0.949621240640999,
        "8": 0.19927536179150002,
        "4": 0.4185125039540002,
        "18": 0.5691588362529991,
        "12": 0.6009789760809999,
        "17": 0.48479405839200057,
        "7": 0.23842544605850016,
        "16": 0.28336540997449977,
        "14": 0.06036624468650007,
        "13": 0.04260779136050022,
        "2": 0.02065452186049993,
        "1": 0.02454134236900001
      },
      "n_cut_edges": 2361
    }

This method has a few advantages: 

i. The data is easy to read
ii. In the event that the run is interrupted (which happens more often than 
    we would like), the data is still saved up to the point of interruption.

The data can then be read back in with something like

.. code-block:: python

    import json

    with open("PA_output.jsonl", "r") as f:
        for line in f:
            data = json.loads(line)
            # Do something with the data


Pandas DataFrames
-----------------

Another method that can be particularly useful
when experimenting with different redistricting ensembles
is to store the data in a pandas dataframe.


.. code-block:: python

    import pandas as pd
    random.seed(42)

    district_data = []  

    for i, partition in enumerate(chain):
        for district_name in partition["population"].keys():
            population = partition["population"][district_name]
            area = partition["area"][district_name]
            n_cut_edges = len(partition["cut_edges"])
            district_data.append((i, district_name, population, area, n_cut_edges))

    df = pd.DataFrame(
        district_data, 
        columns=[
            'step', 
            'district_name', 
            'population', 
            'area', 
            'n_cut_edges'
        ]
    )


The utility of this method is shown in the ability to use dataframe
views to easily filter and manipulate the data. For example, if
we wanted to look at the data for step 11, we could write something
like:

.. code-block:: python

    df[df['step'] == 11]

which will produce:

+-----+------+---------------+------------+----------+-------------+
|     | step | district_name | population |   area   | n_cut_edges |
+=====+======+===============+============+==========+=============+
| 198 |  11  |       3       |   704364   | 0.883639 |    2103     |
+-----+------+---------------+------------+----------+-------------+
| 199 |  11  |       10      |   709547   | 2.228103 |    2103     |
+-----+------+---------------+------------+----------+-------------+
| 200 |  11  |       9       |   712201   | 0.801655 |    2103     |
+-----+------+---------------+------------+----------+-------------+
| 201 |  11  |       5       |   699705   | 1.639986 |    2103     |
+-----+------+---------------+------------+----------+-------------+
| 202 |  11  |       15      |   706694   | 0.744557 |    2103     |
+-----+------+---------------+------------+----------+-------------+
| 203 |  11  |       6       |   708502   | 0.351298 |    2103     |
+-----+------+---------------+------------+----------+-------------+
| 204 |  11  |       11      |   705406   | 0.948691 |    2103     |
+-----+------+---------------+------------+----------+-------------+
| 205 |  11  |       8       |   702576   | 0.109261 |    2103     |
+-----+------+---------------+------------+----------+-------------+
| 206 |  11  |       4       |   705669   | 0.418513 |    2103     |
+-----+------+---------------+------------+----------+-------------+
| 207 |  11  |       18      |   705847   | 0.569159 |    2103     |
+-----+------+---------------+------------+----------+-------------+
| 208 |  11  |       12      |   695032   | 2.954248 |    2103     |
+-----+------+---------------+------------+----------+-------------+
| 209 |  11  |       17      |   695142   | 0.237470 |    2103     |
+-----+------+---------------+------------+----------+-------------+
| 210 |  11  |       7       |   711035   | 0.018885 |    2103     |
+-----+------+---------------+------------+----------+-------------+
| 211 |  11  |       16      |   699557   | 0.283365 |    2103     |
+-----+------+---------------+------------+----------+-------------+
| 212 |  11  |       14      |   705526   | 0.060366 |    2103     |
+-----+------+---------------+------------+----------+-------------+
| 213 |  11  |       13      |   705028   | 0.042608 |    2103     |
+-----+------+---------------+------------+----------+-------------+
| 214 |  11  |       2       |   705218   | 0.021515 |    2103     |
+-----+------+---------------+------------+----------+-------------+
| 215 |  11  |       1       |   707880   | 0.221007 |    2103     |
+-----+------+---------------+------------+----------+-------------+

