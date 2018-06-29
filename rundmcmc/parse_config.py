import functools
import configparser

import matplotlib.pyplot as plt

import rundmcmc.make_graph as mgs
import rundmcmc.validity as valids
import rundmcmc.updaters as updates
import rundmcmc.scores as scores
import rundmcmc.proposals as proposals
import rundmcmc.accept as accepts

from rundmcmc.partition import Partition
from rundmcmc.chain import MarkovChain
from rundmcmc.run import pipe_to_table


def outputfunc(table, scores):
    """Function that processes the output of a chain run.
    (should probably be in a different file at some point
    in the future)

    outputs a window plot of histograms of logged scores
    """
    numrows = 2
    numcols = int(len(scores) / numrows)
    numrows = max(numrows, 1)
    numcols = max(numcols, 1)
    fig, axes = plt.subplots(ncols=numcols, nrows=numrows)

    scoreNames = [x for x in scores.keys()][: numrows * numcols]
    quadrants = {
        key: (int(i / numcols), i % numcols)
        for i, key in enumerate(scoreNames)
    }

    initial_scores = table[0]

    for key in scores:
        quadrant = quadrants[key]
        axes[quadrant].hist(table[key], bins=50)
        axes[quadrant].set_title(key)
        axes[quadrant].axvline(x=initial_scores[key], color='r')
    plt.show()


def sLogType(typestr):
    """return the type of logger to use for scores"""
    if typestr == "pipe_to_table":
        return pipe_to_table
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


def gsource_gdata(configGraphSource, configGraphData):
    """Create a graph from the config file GRAPH_SOURCE and GRAPH_DATA sections"""
    ID = configGraphData['id']
    POP = configGraphData['pop']
    AREA = configGraphData['area']
    CD = configGraphData['cd']
    # create graph from data and load required data
    graph = mgs.construct_graph(configGraphSource['gSource'], ID, [POP, AREA, CD])
    return graph, POP, AREA, CD


def vsource_vdata(graph, configVoteSource, configVoteData):
    """Add data to graph from the config file VOTE_SOURCE and VOTE_DATA sections"""
    source = configVoteSource['vSource']
    geoid = configVoteSource['vSourceID']
    cols_to_add = [x for x in configVoteData.values()]
    mdata = mgs.get_list_of_data(source, cols_to_add, geoid)
    mgs.add_data_to_graph(mdata, graph, cols_to_add, geoid)


def read_basic_config(configFileName):
    """Reads basic configuration file and sets up a chain run

    :configFileName: relative path to config file
    :returns: Partition instance and MarkovChain instance

    """
    # set up the config file parser
    config = configparser.ConfigParser()
    config.read(configFileName)

    # SET UP GRAPH AND PARTITION SECTION
    # make sure the config file has graph information in it
    if (not config.has_section('GRAPH_DATA')) or (not config.has_section('GRAPH_SOURCE')):
        raise Exception("ERROR: config needs a GRAPH_DATA section and a GRAPH_SOURCE section")
    if not all(x in list(config['GRAPH_DATA'].keys()) for x in required_graph_fields()):
        elements = " ".join(required_graph_fields())
        raise Exception("ERROR: graph_data must contain all of the following fields:%s" % elements)

    # create graph and get global names for required graph attributes
    graph, POP, AREA, CD = gsource_gdata(config['GRAPH_SOURCE'], config['GRAPH_DATA'])
    # if there is more data to add to graph (e.g. voting data in a csv)
    if config.has_section('VOTE_DATA_SOURCE'):
        vsource_vdata(graph, config['VOTE_DATA_SOURCE'], config['VOTE_DATA'])
        vlist = [x for x in config['VOTE_DATA'].values()]

    # construct initial districting plan
    assignment = {x[0]: x[1][CD] for x in graph.nodes(data=True)}

    # set up validator functions and create Validator class instance
    validators = [valids.fast_connected]
    if config.has_section('VALIDITY') and len(list(config['VALIDITY'].keys())) > 0:
        validators = [getattr(valids, x) for x in config['VALIDITY'].values()]
    validators = valids.Validator(validators)

    # set up baseline updaters for running chain with polsby-popper and other metrics
    updaters = {'population': updates.Tally(POP, alias='population'),
            'perimeters': updates.perimeters,
            'exterior_boundaries': updates.exterior_boundaries,
            'boundary_nodes': updates.boundary_nodes,
            'cut_edges': updates.cut_edges,
            'cut_edges_by_part': updates.cut_edges_by_part,
            'polsby_popper': updates.polsby_popper_updater,
            'areas': updates.Tally(AREA, alias="areas")}

    for v in vlist:
        updaters[v] = updates.Tally(v)
    # create partition
    initial_partition = Partition(graph, assignment, updaters)
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

    # create markovchain instance
    chain = MarkovChain(proposal, validators, accept, initial_partition, num_steps)
    # END SET UP MARKOVCHAIN RUN SECTION

    # SET UP DATA PROCESSOR FOR CHAIN RUN

    # get evaluation scores to compute and the columns to use for each
    eval_scores = ''
    if config.has_section('EVALUATION_SCORES'):
        eval_list = config['EVALUATION_SCORES'].values()
        eval_scores = {x.split(',')[0]:
                scores_arg_placement(x.split(',')[0], x.split(',')[1:]) for x in eval_list}
        if config.has_section('EVALUATION_SCORES_DATA'):
            scoreLogType = sLogType(config['EVALUATION_SCORES_DATA']['evalScoreLogType'])
            chainfunc = functools.partial(scoreLogType, handlers=eval_scores)
        else:
            def chainfunc(thing):
                pass
    else:
        def chainfunc(thing):
            pass

    # END SET UP DATA PROCESSOR FOR CHAIN RUN

    return chain, chainfunc, eval_scores, outputfunc
