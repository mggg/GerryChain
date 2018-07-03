import functools
import configparser

import rundmcmc.make_graph as mgs
import rundmcmc.validity as valids
import rundmcmc.updaters as updates
import rundmcmc.scores as scores
import rundmcmc.proposals as proposals
import rundmcmc.accept as accepts
import rundmcmc.output as outputs

from rundmcmc.partition import Partition
from rundmcmc.chain import MarkovChain
from rundmcmc.run import pipe_to_table, flips_to_dict


def nothingFunc(args):
    pass


def scoresLogType(typestr):
    """return the type of logger to use for scores"""
    if typestr == "pipe_to_table":
        return pipe_to_table
    elif typestr == "flips_to_dict":
        return flips_to_dict
    else:
        print("ERROR: TYPE OF LOGGER NOT SUPPORTED")


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
            return functools.partial(func, col1=args[0], col2=args[1])
        else:
            func = getattr(scores, funcName)
            return functools.partial(func, proportion_column_name=args[0])

    elif hasattr(updates, funcName):
        func = getattr(updates, funcName)
        return func

    elif hasattr(valids, funcName):
        func = getattr(valids, funcName)
        return func


def required_graph_fields():
    """The minimum data required to run MCMC on a state at the moment"""
    return ['id', 'pop', 'area', 'cd']


def gsource_gdata(config, graphSource, graphData):
    """Create a graph from the config file GRAPH_SOURCE and GRAPH_DATA sections"""

    # make sure the config file has graph information in it
    if (not config.has_section(graphData)) or (not config.has_section(graphSource)):
        raise Exception("ERROR: config needs a GRAPH_DATA section and a GRAPH_SOURCE section")
    if not all(x in list(config[graphData].keys()) for x in required_graph_fields()):
        elements = " ".join(required_graph_fields())
        raise Exception("ERROR: graph_data must contain all of the following fields: %s" % elements)
    configGraphData = config[graphData]
    configGraphSource = config[graphSource]

    ID = configGraphData['id']
    POP = configGraphData['pop']
    AREA = configGraphData['area']
    CD = configGraphData['cd']
    # create graph from data and load required data
    graph = mgs.construct_graph(configGraphSource['gSource'], ID, [POP, AREA, CD])
    return graph, POP, AREA, CD


def vsource_vdata(graph, config, voteSource, voteData):
    """Add data to graph from the config file VOTE_SOURCE and VOTE_DATA sections"""
    if not config.has_section(voteSource):
        return []

    configVoteSource = config[voteSource]
    configVoteData = config[voteData]
    source = configVoteSource['vSource']
    geoid = configVoteSource['vSourceID']

    cols_to_add = [x for x in configVoteData.values()]
    mdata = mgs.get_list_of_data(source, cols_to_add, geoid)
    mgs.add_data_to_graph(mdata, graph, cols_to_add, geoid)

    return [x for x in configVoteData.values()]


def escores_edata(config, evalScores, evalScoresData):
    eval_scores = ''
    outputFileName = None
    scoreVisType = None
    chainfunc = nothingFunc

    if config.has_section('EVALUATION_SCORES'):
        eval_list = config['EVALUATION_SCORES'].values()
        funcs, cols = zip(*[(x.split(',')[0], x.split(',')[1:]) for x in eval_list])

        eval_scores = {funcs[x]: scores_arg_placement(funcs[x], cols[x]) for x in range(len(funcs))}

        if config.has_section('EVALUATION_SCORES_DATA'):
            if 'evalscorelogtype' in list(config['EVALUATION_SCORES_DATA'].keys()):
                scoreLogType = scoresLogType(config['EVALUATION_SCORES_DATA']['evalscorelogtype'])
                chainfunc = functools.partial(scoreLogType, handlers=eval_scores)

            if 'vistype' in list(config['EVALUATION_SCORES_DATA'].keys()):
                scoreVisType = getattr(outputs, config['EVALUATION_SCORES_DATA']['vistype'])

            if 'savefilename' in list(config['EVALUATION_SCORES_DATA'].keys()):
                outputFileName = config['EVALUATION_SCORES_DATA']['savefilename']

    return eval_scores, chainfunc, funcs, scoreVisType, outputFileName


def dependencies(scoreType, POP, AREA):
    """returns the updaters dependencies for whatever scoretype
    is passed in. To be used as a checking device against the
    user-specified validators and score functions
    NOTE: this does not check efficiency/mean-median/mean-thirdian.

    :scoreType: name of function to check dependencies of
    :POP: name of population column in graph object
    :AREA: name of area column in graph object

    """
    depends = {}
    if scoreType == "areas":
        depends = {"areas": updates.Tally(AREA, alias="areas")}

    elif scoreType == "population":
        depends = {"population": updates.Tally(POP, alias="population")}

    elif scoreType == "perimeters":
        depends = {
                'boundary_nodes': updates.boundary_nodes,
                'cut_edges': updates.cut_edges,
                'cut_edges_by_part': updates.cut_edges_by_part,
                'exterior_boundaries': updates.exterior_boundaries,
                'perimeters': updates.perimeters
                }

    elif scoreType == "polsby_popper":
        depends = {**dependencies("areas", POP, AREA), **dependencies("perimeters", POP, AREA)}
        depends["polsby_popper"] = updates.polsby_popper_updater

    elif scoreType == "L1_reciprocal_polsby_popper":
        depends = dependencies("polsby_popper", POP, AREA)

    elif scoreType == "no_vanishing_districts":
        depends = dependencies("population", POP, AREA)

    elif scoreType == "fast_connected":
        depends = {}

    elif scoreType == "within_percent_of_ideal_population":
        depends = dependencies("population", POP, AREA)

    elif scoreType == "p_value":
        depends = {"mean_median": scores.mean_median, "mean_thirdian": scores.mean_thirdian}

    return depends


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
    if config.has_section('VALIDITY') and len(list(config['VALIDITY'].keys())) > 0:
        validators = [getattr(valids, x) for x in config['VALIDITY'].values()]
        validatorsUpdaters.extend(list(config['VALIDITY'].values()))
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
