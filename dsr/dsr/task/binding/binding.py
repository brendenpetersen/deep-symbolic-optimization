import os
import numpy as np
import pandas as pd
import torch
import yaml
from collections import OrderedDict

import dsr
from dsr.library import Library, Token
from dsr.functions import create_tokens
# from dsr.program import Program
import dsr.constants as constants

import abag_ml.rl_environment_objects as rl_env_obj
import vaccine_advance_core.featurization.vaccine_advance_core_io as vac_io
import abag_agent_setup.expand_allowed_mutant_menu as abag_agent_setup_eamm


def diff_letters(a, b):
    return sum ( a[i] != b[i] for i in range(len(a)) )


def make_binding_task(name, paths, mode, function_set):
    """
    Factory function for ab/ag binding affinity rewards. 

    Parameters
    ----------

    name : str
        Experiment name.

    paths : dict
        Path to files used to run Gaussian Process-based binding environment.
    
    function_set : list
        List of possible discrete symbols that can be allocated.

    Returns
    -------

    task : Task
        Dynamically created Task object whose methods contains closures.
    """

    # get master sequence
    master_seqrecord = vac_io.list_of_seqrecords_from_fasta(
        os.path.join(paths['base_path'], paths['master_seqrecord_fasta'])
    )[0]

    # load Gaussian Process data
    x = torch.load(os.path.join(paths['base_path'], paths['history_x_tensor']))
    i = torch.load(os.path.join(paths['base_path'], paths['history_i_tensor']))
    y = torch.load(os.path.join(paths['base_path'], paths['history_y_tensor']))

    env = rl_env_obj.GPModelEnvironment(
        os.path.join(paths['base_path'], paths['model_weights_pth']),
        os.path.join(paths['base_path'], paths['master_structure']),
        master_seqrecord,
        ('A', 'C'),  # TODO: check vs. master_structure
        'A',
        torch.ones((1,), dtype=torch.long),  # TODO: check if this must be an int or if it can be a torch.long
        history_studies=None,
        history_tensor_x=x,
        history_tensor_i=i,
        history_tensor_y=y,
        is_sparse=paths['model_is_sparse'],
        is_mtl=paths['model_is_mtl'],
        parallel_featurization=False,
        use_gpu=paths['use_gpu'] if 'use_gpu' in paths else True
    )

    # load menu file information
    try:
        with open(paths['menu_file']) as fh:
            menu_config = yaml.full_load(fh)
    except FileNotFoundError:
        print("Could not open/read file:", paths['menu_file'])

    # define amino acids as tokens
    tokens = [Token(None, aa, arity=1, complexity=1) for aa in constants.AMINO_ACIDS]
    library = Library(tokens)

    # load master sequence - new samples will be based on it
    master_sequence = menu_config['Sequence']['master_sequence']
    new_sequence = [library[aa] for aa in master_sequence]

    # store allowed mutation in a dict for faster access
    allowed_mutations = OrderedDict()
    for p in menu_config['AllowedMutations']:
        # Per Tom: positions in the yaml file starts from 1 and not 0
        allowed_mutations[p[0] - 1] = p[1]


    def assemble_sequence(p):
        ''' Create full sequence from the master sequence and generated mutations
            from the RL controller. This is needed when no neighborhood
            info is used by the RL agent (use_context=False). '''
        # full mode: just get the traversal
        if mode == 'full':
            return p.traversal

        # short mode: get master sequence and fill the blanks with RL's proposed mutations
        short_seq = p.traversal
        for idx, aa in zip(allowed_mutations, short_seq):
            new_sequence[idx] = aa
        return new_sequence


    def reward(p):
        """ Compute reward value for a given program (sequence). 

            Parameters
            ----------
            p : Program
                A program that contains a single sequence.
            
            Returns:
            ----------
            rwd : Reward value

        """
        sampled_sequence = assemble_sequence(p)
        rwd = env.reward(''.join([t.name for t in sampled_sequence]))
        rwd = rwd.item()
        return rwd


    def evaluate(p):
        """ Compute certain statistics of the program (sequence).

            Parameters
            ----------
            p : Program
                A program that contains a single sequence.
            
            Returns:
            ----------
            info : statistics 

        """
        info = {}
        return info

    extra_info = {}
    task = dsr.task.Task(reward_function=reward,
                         evaluate=evaluate,
                         library=library,
                         stochastic=False,
                         task_type='binding',
                         extra_info=extra_info)

    return task
