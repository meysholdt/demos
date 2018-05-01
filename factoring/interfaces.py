from __future__ import division

import time
import logging

from collections import OrderedDict

import dwavecsp
from dwave.system.samplers import DWaveSampler
import minorminer
import dimod

log = logging.getLogger(__name__)


def validate_input(ui, range_):
    start = range_[0]
    stop = range_[-1]

    if not isinstance(ui, int):
        raise ValueError("Input type must be int")

    if ui not in range_:
        raise ValueError("Input must be between {} and {}".format(start, stop))


def factor(P, use_saved_embedding=True):

    ####################################################################################################
    # get circuit
    ####################################################################################################

    construction_start_time = time.time()

    validate_input(P, range(2 ** 6))

    # get constraint satisfaction problem
    csp = dwavecsp.factories.multiplication_circuit(3)

    # we know that multiplication_circuit() has created these variables
    p_vars = ['p0', 'p1', 'p2', 'p3', 'p4', 'p5']

    # convert P from decimal to binary
    fixed_variables = dict(zip(reversed(p_vars), "{:06b}".format(P)))
    fixed_variables = {var: int(x) for(var, x) in fixed_variables.items()}

    # fix product qubits
    for var, value in fixed_variables.items():
        csp.fix_variable(var, value)

    # get binary quadratic model
    bqm = dwavecsp.stitch(csp, min_classical_gap=.1)

    log.debug('bqm construction time: %s', time.time() - construction_start_time)

    ####################################################################################################
    # run problem
    ####################################################################################################

    sample_time = time.time()

    # get QPU sampler
    sampler = DWaveSampler()
    _, target_edgelist, target_adjacency = sampler.structure

    if use_saved_embedding:
        # load a pre-calculated embedding
        from factoring.embedding import embedding
    else:
        # get the embedding
        embedding = minorminer.find_embedding(bqm.quadratic, target_edgelist)
        if bqm and not embedding:
            raise ValueError("no embedding found")
        # this should change in later versions
        if isinstance(embedding, list):
            embedding = dict(enumerate(embedding))

    # apply the embedding to the given problem to map it to the sampler
    bqm_embedded = dimod.embed_bqm(bqm, embedding, target_adjacency, 3.0)

    # draw samples from the QPU
    kwargs = {}
    if 'num_reads' in sampler.parameters:
        kwargs['num_reads'] = 50
    if 'answer_mode' in sampler.parameters:
        kwargs['answer_mode'] = 'histogram'
    response = sampler.sample(bqm_embedded, **kwargs)

    # convert back to the original problem space
    response = dimod.unembed_response(response, embedding, source_bqm=bqm)

    log.debug('embedding and sampling time: %s', time.time() - sample_time)

    ####################################################################################################
    # output results
    ####################################################################################################

    output = {
        "results": [],
        #    {
        #        "a": Number,
        #        "b": Number,
        #        "valid": Boolean,
        #        "numOfOccurrences": Number,
        #        "percentageOfOccurrences": Number
        #    }
        "timing": {
            "actual": {
                "qpuProcessTime": None  # microseconds
            }
        },
        "numberOfReads": None
    }

    # we know that multiplication_circuit() has created these variables
    a_vars = ['a0', 'a1', 'a2']
    b_vars = ['b0', 'b1', 'b2']

    # histogram answer_mode should return counts for unique solutions
    if 'num_occurrences' not in response.data_vectors:
        response.data_vectors['num_occurrences'] = [1] * len(response)

    # should equal num_reads
    total = sum(response.data_vectors['num_occurrences'])

    results_dict = OrderedDict()
    for sample, num_occurrences in response.data(['sample', 'num_occurrences']):
        # convert A and B from binary to decimal
        a = b = 0
        for lbl in reversed(a_vars):
            a = (a << 1) | sample[lbl]
        for lbl in reversed(b_vars):
            b = (b << 1) | sample[lbl]
        # aggregate results by unique A and B values (ignoring internal circuit variables)
        if (a, b, P) in results_dict:
            results_dict[(a, b, P)]["numOfOccurrences"] += num_occurrences
            results_dict[(a, b, P)]["percentageOfOccurrences"] = 100 * \
                results_dict[(a, b, P)]["numOfOccurrences"] / total
        else:
            results_dict[(a, b, P)] = {"a": a,
                                       "b": b,
                                       "valid": a * b == P,
                                       "numOfOccurrences": num_occurrences,
                                       "percentageOfOccurrences": 100 * num_occurrences / total}

    output['results'] = list(results_dict.values())
    output['numberOfReads'] = total
    if 'timing' in response.info:
        output['timing']['actual']['qpuProcessTime'] = response.info['timing']['qpu_access_time']

    return output
