========================================================
Advanced Example: Optimizing Using Geographic Quantities
========================================================

In the previous section we saw how to use the ``SingleMetricOptimizer`` to optimize
for plans that contain the minimum number of cut edges. However, sometimes we may wish to
include other geographic quantities in our optimization equation. Obtaining and working
with this sort of data can be a bit more involved, so here we will show how to use the
``requests`` package to download data directly from the Census API and how to use that data
for optimization.



Getting the Data
----------------

First, we will need to install the ``requests`` package:

.. code:: bash

    pip install requests

Then we can import the package in the head of our jupyter notebook and download the data:

.. code:: python

    import os
    import pandas as pd
    import requests

    shape_url = "https://www2.census.gov/geo/tiger/TIGER2020PL/LAYER/BG/2020/tl_2020_01_bg20.zip"

    shape_response = requests.get(shape_url)
    shape_response.raise_for_status()

    with open("tl_2020_01_bg20.zip", "wb") as f:
        f.write(shape_response.content)

    pop_url = "https://api.census.gov/data/2020/dec/pl"
    pop_params = {
        "get": "group(P1)",
        "for": "block group:*",
        "in": "state:01 county:*",
     }


    # Note that you will need to get your own Census API key and set it as an environment variable
    # or replace the "REPLACE_WITH_YOUR_KEY" string with your key.
    census_api_key = os.environ.get("CENSUS_API_KEY", "REPLACE_WITH_YOUR_KEY")

    pop_params["key"] = census_api_key

    pop_response = requests.get(
        pop_url,
        params=pop_params,
        timeout=30,
    )
    pop_response.raise_for_status()

    pop_df = pd.DataFrame(pop_response.json()[1:], columns=pop_response.json()[0])

    pop_df.to_pickle("01_bg_P1_2020.pkl")

You can request a key from the `Census API key signup page
<https://api.census.gov/data/key_signup.html>`_. Store it in the ``CENSUS_API_KEY`` environment
variable rather than putting it directly in your notebook. We have saved the downloaded data for
later so that it is easier to use in the next section.

Preparing the Data
------------------

We are now ready to work with the optimizer. First, we will need to import the necessary packages:

.. code:: python

    from gerrychain import Graph, GeographicPartition, MarkovChain
    from gerrychain.updaters import Tally
    from gerrychain.metrics.compactness import polsby_popper
    from gerrychain.proposals import recom, build_recom_proposal_fn
    from gerrychain.tree import bipartition_tree
    from gerrychain.accept import always_accept
    from gerrychain.optimization import SingleMetricOptimizer
    from functools import partial
    import numpy as np
    import pandas as pd
    import geopandas as gpd
    import random

    rng = random.Random(2024)


Now we need to import the data and check the Coordinate Reference System (CRS) for reasons that
will be explained momentarily:

.. code:: python

    gdf = gpd.read_file("tl_2020_01_bg20.zip")
    gdf.crs


.. code:: console

    <Geographic 2D CRS: EPSG:4269>
    Name: NAD83
    Axis Info [ellipsoidal]:
    - Lat[north]: Geodetic latitude (degree)
    - Lon[east]: Geodetic longitude (degree)
    Area of Use:
    - name: North America - onshore and offshore: Canada - Alberta; British Columbia; Manitoba; New Brunswick; Newfoundland and Labrador; Northwest Territories; Nova Scotia; Nunavut; Ontario; Prince Edward Island; Quebec; Saskatchewan; Yukon. Puerto Rico. United States (USA) - Alabama; Alaska; Arizona; Arkansas; California; Colorado; Connecticut; Delaware; Florida; Georgia; Hawaii; Idaho; Illinois; Indiana; Iowa; Kansas; Kentucky; Louisiana; Maine; Maryland; Massachusetts; Michigan; Minnesota; Mississippi; Missouri; Montana; Nebraska; Nevada; New Hampshire; New Jersey; New Mexico; New York; North Carolina; North Dakota; Ohio; Oklahoma; Oregon; Pennsylvania; Rhode Island; South Carolina; South Dakota; Tennessee; Texas; Utah; Vermont; Virginia; Washington; West Virginia; Wisconsin; Wyoming. US Virgin Islands. British Virgin Islands.
    - bounds: (167.65, 14.92, -40.73, 86.45)
    Datum: North American Datum 1983
    - Ellipsoid: GRS 1980
    - Prime Meridian: Greenwich


In this example, we will be interested in optimizing the average Polsby-Popper score for
the example data, but before we can do that, we need to make sure that the CRS for
our data is appropriate for the measurements we wish to take. For this example, this means that
we would like  avoid coordinate systems like the geographic coordinate system (lat, long) which
measures distances in degrees in favor of something like a Mercator or transverse Mercator
projection which measures distances in meters and is subject to less distortion.

We can see that the Census uses the CRS ``EPSG:4269`` which is a geographic coordinate system and
not useful for computing things like the Polsby-Popper score, so we need to transform the data
mildly before we can use it. In general, to find a good choice of CRS, it is best to consult
the official EPSG website `epsg.io <https://epsg.io>`_. In this case, we are working with Alabama,
and we know that the Albers Equal Area Conic projection with epsg code 5070 is a good choice. So
we will modify our geodataframe to use this CRS and then make a graph from it:

.. code:: python

    gdf.to_crs(epsg=5070, inplace=True)
    graph = Graph.from_geodataframe(gdf)
    # And we should check to make sure that the CRS is set properly
    graph.data.crs

.. code:: console

    <Projected CRS: EPSG:5070>
    Name: NAD83 / Conus Albers
    Axis Info [cartesian]:
    - X[east]: Easting (metre)
    - Y[north]: Northing (metre)
    Area of Use:
    - name: United States (USA) - CONUS onshore - Alabama; Arizona; Arkansas; California; Colorado; Connecticut; Delaware; Florida; Georgia; Idaho; Illinois; Indiana; Iowa; Kansas; Kentucky; Louisiana; Maine; Maryland; Massachusetts; Michigan; Minnesota; Mississippi; Missouri; Montana; Nebraska; Nevada; New Hampshire; New Jersey; New Mexico; New York; North Carolina; North Dakota; Ohio; Oklahoma; Oregon; Pennsylvania; Rhode Island; South Carolina; South Dakota; Tennessee; Texas; Utah; Vermont; Virginia; Washington; West Virginia; Wisconsin; Wyoming.
    - bounds: (-124.79, 24.41, -66.91, 49.38)
    Coordinate Operation:
    - name: Conus Albers
    - method: Albers Equal Area
    Datum: North American Datum 1983
    - Ellipsoid: GRS 1980
    - Prime Meridian: Greenwich

Since we used a shapefile that was directly from the US Census, we will need to add in the population
data to the graph. Here we have the 2020 P1 table from the US Census with the column "P1_001N"
corresponding to the total population of each geograpic unit.

.. code:: python

    population_data = pd.read_pickle("01_bg_P1_2020.pkl")
    population_columns = ["GEO_ID", "NAME", "P1_001N"]
    population_data[population_columns].head()


.. code:: console

                          GEO_ID                                                     NAME P1_001N
    0  1500000US010610503006  Block Group 6, Census Tract 503, Geneva County, Alabama     639
    1  1500000US010610504003  Block Group 3, Census Tract 504, Geneva County, Alabama     950
    2  1500000US010610505001  Block Group 1, Census Tract 505, Geneva County, Alabama    1158
    3  1500000US010610505004  Block Group 4, Census Tract 505, Geneva County, Alabama    1022
    4  1500000US010610506003  Block Group 3, Census Tract 506, Geneva County, Alabama    1386


We now need to merge the population data with the graph data. Unfortunately, the Census data for
the shapefile and for the P1 table do not have consistent formatting for the geoids, so we need
to fix that.


.. code:: python

    # This grabs the UID part of the GEO_ID column and puts it into a new column called GEOID20
    population_data["GEOID20"] = population_data["GEO_ID"].apply(lambda x: x.split("US")[1])

    full_data = pd.merge(population_data, graph.data, on='GEOID20')

    # Check to make sure the number of rows in the full data is the same as the number of rows
    # in the graph.data dataframe. This is a sanity check to make sure we didn't lose any data.
    assert full_data.shape[0] == graph.data.shape[0]

    full_data.set_index("GEOID20", inplace=True)
    full_columns = ["GEO_ID", "P1_001N", "STATEFP20", "COUNTYFP20", "ALAND20"]
    full_data[full_columns].head()




And now we can add the population data to the graph:

.. code:: python

    for node_id in graph.node_indices:
        node_data = graph.node_data(node_id)
        geo_id = node_data["GEOID20"]
        # Note that the pops are np.int64 types, so we convert them to ints here
        node_data["TOTPOP"] = int(full_data.at[geo_id, "P1_001N"])

    graph.node_data(0)


.. code:: console

    {'boundary_node': False,
    'area': 1100226.0333901227,
    'STATEFP20': '01',
    'COUNTYFP20': '033',
    'TRACTCE20': '020200',
    'BLKGRPCE20': '1',
    'GEOID20': '010330202001',
    'NAMELSAD20': 'Block Group 1',
    'MTFCC20': 'G5030',
    'FUNCSTAT20': 'S',
    'ALAND20': 994584,
    'AWATER20': 105643,
    'INTPTLAT20': '+34.7664259',
    'INTPTLON20': '-087.6960323',
    'geometry': <POLYGON ((752587.971 1333045.744, 752581.759 1333117.737, 752581.362 133313...>,
    'TOTPOP': 1171}



Using ``SingleMetricOptimizer``
-------------------------------

There is a ``polsby_popper`` updater in GerryChain, but you need to make sure that the
CRS for your data is correct before you use it. If it is not, then you can run into some issues with
distortion of the geometry. However, we already checked that our CRS is appropriate in this
tutorial, so we don't need to worry. We can now follow the usual workflow laid out in the
`optimization tutorial <https://gerrychain.readthedocs.io/en/latest/user/optimizers/>`_
with the only tweak being that we need to use a ``GeographicPartition`` object instead
of a regular ``Partition`` object for the ``SingleMetricOptimizer`` since we want to use the
``polsby_popper`` updater which relies on the ``area`` and ``perimeter`` updaters.


.. code:: python

    updaters = {
        "population": Tally("TOTPOP", alias="population"),
        "polsby-popper": polsby_popper,
    }

    # We need to use the GeographicPartition class to make sure that area and perimeter
    # updaters are also calculated. These are used in the calculation of the polsby-popper
    # score.
    initial_partition = GeographicPartition.from_random_assignment(
        graph=graph,
        n_parts=4,
        epsilon=0.01,
        pop_col="TOTPOP",
        updaters=updaters,
        rng=rng,
    )

    ideal_population = sum(initial_partition["population"].values())/len(initial_partition)

    opt_metric = lambda x: sum(x["polsby-popper"].values())/len(x)

    POPCOL = "TOTPOP"
    EPS = 0.02
    TOTPOP = sum(graph.node_data(node_id)[POPCOL] for node_id in graph.node_indices)

    proposal = build_recom_proposal_fn(
        pop_col=POPCOL,
        pop_target=TOTPOP/4,
        epsilon=EPS,
    )

    optimizer = SingleMetricOptimizer(
        initial_state=initial_partition,
        proposal=proposal,
        constraints=[],
        optimization_metric=opt_metric,
        maximize=True,
        rng=rng,
    )


    tilt_best = -1
    for i, part in enumerate(optimizer.tilted_run(1000, 0.1, with_progress_bar=True)):
        tilt_best = max(tilt_best, opt_metric(part))


    print(tilt_best)
