import os
import sys
import json
import functools
import configparser
import networkx.readwrite.json_graph as json_graph

import rundmcmc.make_graph as mgs
import rundmcmc.validity as valids
import rundmcmc.updaters as updates
import rundmcmc.scores as scores
import rundmcmc.proposals as proposals
import rundmcmc.accept as accepts
import rundmcmc.output as outputs
import rundmcmc.vis_output as visoutputs

from rundmcmc.partition import Partition
from rundmcmc.chain import MarkovChain
from rundmcmc.run import handle_scores_separately


thismodule = sys.modules[__name__]


def write_hists(a, b, c, filename=''):
    visoutputs.hist_of_table_scores(a[0], a[2], filename)


def write_flips(a, b, c, filename=''):
    with open(filename, "w") as f:
        f.write(a[1])


def write_p_values(a, b, c, filename=''):
    initial_plans = a[0][0]
    output = [outputs.p_value_report(score, a[0][score], initial_plans[score]) for score in a[2]]
    with open(filename, "w") as f:
        f.write(json.dumps(output))


def scores_arg_placement(funcName, args):
    """Instantiate evaluation score functions that
    are either genuine scores (in scores.py) or else
    are updaters/validators (in updaters.py or validity.py)
    with default parameters based on voting data columns.
    At the moment, there are 3 types of functions:

    1-parameter(in updaters and validity) just takes partition

    2-parameter(e.g. mean-median and mean-thirdian) takes partition and colname

    3-parameter(efficiency gap) takes partition and 2 colnames

    NOTE: all 2-parameter types use the name proportion_column_name
    for the argument. This is what we fill with a column name
    """
    if hasattr(scores, funcName):
        if funcName == "efficiency_gap":
            func = getattr(scores, funcName)
            return [functools.partial(func, col1=args[2 * i], col2=args[2 * i + 1])
                    for i in range(int(len(args) / 2))]
        else:
            func = getattr(scores, funcName)
            return [functools.partial(func, proportion_column_name=args[i])
                    for i in range(len(args))]

    elif hasattr(updates, funcName):
        func = getattr(updates, funcName)
        return [func]

    elif hasattr(valids, funcName):
        func = getattr(valids, funcName)
        return [func]
    else:
        raise NotImplementedError(f"{funcName} not supported")


def dependencies(scoreType, POP, AREA):
    """returns the updaters dependencies for whatever scoretype
    is passed in. To be used as a checking device against the
    user-specified validators and score functions
    NOTE: this does not check efficiency/mean-median/mean-thirdian.

    :scoreType: name of function to check dependencies of
    :POP: name of population column in graph object
    :AREA: name of area column in graph object

    """
    depends = {
            "areas": updates.Tally(AREA, alias="areas"),
            "population": updates.Tally(POP, alias="population"),
            'boundary_nodes': updates.boundary_nodes,
            'cut_edges': updates.cut_edges,
            'cut_edges_by_part': updates.cut_edges_by_part,
            'exterior_boundaries': updates.exterior_boundaries,
            'interior_boundaries': updates.interior_boundaries,
            'perimeters': updates.perimeters
            }

    if "population_balance" in scoreType:
        depends = {"population": updates.Tally(POP, alias="population")}

    elif "polsby_popper" in scoreType:
        depends["polsby_popper"] = updates.polsby_popper
        depends['cut_edges'] = updates.cut_edges
        depends['cut_edges_by_part'] = updates.cut_edges_by_part

    elif scoreType == "no_vanishing_districts":
        depends['cut_edges'] = updates.cut_edges
        depends['cut_edges_by_part'] = updates.cut_edges_by_part

    elif scoreType == "fast_connected":
        pass

    elif scoreType == "no_more_disconnected":
        pass

    elif "within_percent_of_ideal_population" in scoreType:
        depends['cut_edges'] = updates.cut_edges
        depends['cut_edges_by_part'] = updates.cut_edges_by_part

    elif scoreType == "p_value":
        depends["mean_median"] = scores.mean_median
        depends["mean_thirdian"] = scores.mean_thirdian
        depends['cut_edges'] = updates.cut_edges
        depends['cut_edges_by_part'] = updates.cut_edges_by_part

    return depends


def gsource_gdata(config, graphSource, graphData):
    """Create a graph from the config file GRAPH_SOURCE and GRAPH_DATA sections"""
    # make sure the config file has graph information in it
    graph_source_field = "gSource"
    save_graph_field = "save_json"
    required_graph_data_fields = ['id', 'pop', 'area', 'cd']

    if not config.has_section(graphData):
        raise configparser.NoSectionError(graphData)
    if not config.has_section(graphSource):
        raise configparser.NoSectionError(graphSource)

    configGraphData = config[graphData]
    configGraphSource = config[graphSource]

    missing = [x for x in required_graph_data_fields if x not in configGraphData]

    if missing:
        missing_str = " ".join(missing)
        raise configparser.NoOptionError(missing_str, graphData)

    if graph_source_field not in configGraphSource:
        raise configparser.NoOptionError(graph_source_field, graphSource)

    ID = configGraphData['id']
    POP = configGraphData['pop']
    AREA = configGraphData['area']
    CD = configGraphData['cd']
    # create graph from data and load required data

    path = configGraphSource[graph_source_field]
    save_graph = False

    if save_graph_field in configGraphSource:
        save_graph = True
        if os.path.isfile(configGraphSource[save_graph_field]):
            print("trying to load graph from", path)
            path = configGraphSource[save_graph_field]
            save_graph = False

    graph = mgs.construct_graph(path, ID, [POP, AREA, CD])

    if save_graph:
        print("saving graph to", configGraphSource[save_graph_field])
        with open(configGraphSource[save_graph_field], "w") as f:
            json.dump(json_graph.adjacency_data(graph), f)

    return graph, POP, AREA, CD


def vsource_vdata(graph, config, voteSource, voteData):
    """Add data to graph from the config file VOTE_SOURCE and VOTE_DATA sections"""
    if not config.has_section(voteSource):
        return []

    configVoteSource = config[voteSource]
    configVoteData = config[voteData]
    source = configVoteSource['vSource']
    geoid = configVoteSource['vSourceID']

    cols_to_add = list(configVoteData.values())
    mdata = mgs.get_list_of_data(source, cols_to_add, geoid)
    mgs.add_data_to_graph(mdata, graph, cols_to_add, geoid)

    return list(configVoteData.values())


def escores_edata(config, evalScores, evalScoresData):
    eval_scores = ''
    output_file_name = None
    output_vis_type = lambda x, y, z: 0
    chainfunc = lambda x: 0
    eval_list = []
    funcs = []

    if config.has_section('EVALUATION_SCORES'):
        eval_list = config['EVALUATION_SCORES'].values()
        funcs, cols = zip(*[(x.split(',')[0], x.split(',')[1:]) for x in eval_list])

        eval_scores = {funcs[x] + str(i): s
                for x in range(len(funcs)) for i, s in
                enumerate(scores_arg_placement(funcs[x], cols[x]))}

        if config.has_section('EVALUATION_SCORES_LOG'):
            fname = {key: value for key, value in config['SAVEFILENAME'].items()}

            if "write_flips" in fname:
                eval_scores["flips"] = updates.flips

            output_funcs = [functools.partial(getattr(thismodule, x), filename=fname[x])
                    for x in fname.keys()]

            output_vis_type = lambda x, y, z: [a(x, y, z) for a in output_funcs]

        chainfunc = functools.partial(handle_scores_separately, handlers=eval_scores)

    return eval_scores, chainfunc, eval_list, output_vis_type, output_file_name


def read_basic_config(configFileName):
    """Reads basic configuration file and sets up a chain run

    :configFileName: relative path to config file
    :returns: Partition instance and MarkovChain instance

    """
    # set up the config file parser
    config = configparser.ConfigParser()
    config.read(configFileName)

    # SET UP GRAPH AND PARTITION SECTION
    # create graph and get global names for required graph attributes
    graph, POP, AREA, CD = gsource_gdata(config, 'GRAPH_SOURCE', 'GRAPH_DATA')

    voteDataList = vsource_vdata(graph, config, 'VOTE_DATA_SOURCE', 'VOTE_DATA')
    # create a list of vote columns to update
    DataUpdaters = {v: updates.Tally(v) for v in voteDataList}
    # construct initial districting plan
    assignment = {x[0]: x[1][CD] for x in graph.nodes(data=True)}
    # set up validator functions and create Validator class instance
    validatorsUpdaters = []
    validators = []
    if config.has_section('VALIDITY') and len(list(config['VALIDITY'].keys())) > 0:
        validators = list(config['VALIDITY'].values())
        for i, x in enumerate(validators):
            if len(x.split(',')) == 1:
                validators[i] = getattr(valids, x)
            else:
                [y, z] = x.split(',')
                validators[i] = valids.WithinPercentRangeOfBounds(getattr(valids, y), z)
        validatorsUpdaters.extend([x.split(',')[0] for x in config['VALIDITY'].values()])

    validators = valids.Validator(validators)
    # add updaters required by this list of validators to list of updaters
    for x in validatorsUpdaters:
        DataUpdaters.update(dependencies(x, POP, AREA))
    # END SET UP GRAPH AND PARTITION SECTION

    # SET UP MARKOVCHAIN RUN SECTION
    # set up parameters for markovchain run
    chainparams = config['MARKOV_CHAIN']
    # number of steps to run
    num_steps = 1000
    if 'num_steps' in list(chainparams.keys()):
        num_steps = int(chainparams['num_steps'])
    # type of flip to use
    proposal = proposals.propose_random_flip
    if 'proposal' in list(chainparams.keys()):
        proposal = getattr(proposals, chainparams['proposal'])
    # acceptance function to use
    accept = accepts.always_accept
    if 'accept' in list(chainparams.keys()):
        accept = getattr(accepts, chainparams['accept'])
    # END SET UP MARKOVCHAIN RUN SECTION

    # SET UP DATA PROCESSOR FOR CHAIN RUN
    # get evaluation scores to compute and the columns to use for each
    escores, cfunc, elist, sVisType, outFName = escores_edata(config,
            "EVALUATION_SCORES",
            "EVALUATION_SCORES_DATA")

    # add evaluation scores updaters to list of updators
    for x in elist:
        DataUpdaters.update(dependencies(x, POP, AREA))

    # END SET UP DATA PROCESSOR FOR CHAIN RUN
    updaters = DataUpdaters

    # create markovchain instance
    initial_partition = Partition(graph, assignment, updaters)
    chain = MarkovChain(proposal, validators, accept, initial_partition, num_steps)

    return chain, cfunc, escores, sVisType, outFName
