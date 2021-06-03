"""Utility functions used in deep symbolic regression."""

import collections
import copy
import os
import functools
import numpy as np
import time


def is_float(s):
    """Determine whether str can be cast to float."""

    try:
        float(s)
        return True
    except ValueError:
        return False


# Adapted from: https://stackoverflow.com/questions/32791911/fast-calculation-of-pareto-front-in-python
def is_pareto_efficient(costs):
    """
    Find the pareto-efficient points given an array of costs.

    Parameters
    ----------

    costs : np.ndarray
        Array of shape (n_points, n_costs).

    Returns
    -------

    is_efficient_maek : np.ndarray (dtype:bool)
        Array of which elements in costs are pareto-efficient.
    """

    is_efficient = np.arange(costs.shape[0])
    n_points = costs.shape[0]
    next_point_index = 0  # Next index in the is_efficient array to search for
    while next_point_index<len(costs):
        nondominated_point_mask = np.any(costs<costs[next_point_index], axis=1)
        nondominated_point_mask[next_point_index] = True
        is_efficient = is_efficient[nondominated_point_mask]  # Remove dominated points
        costs = costs[nondominated_point_mask]
        next_point_index = np.sum(nondominated_point_mask[:next_point_index])+1
    is_efficient_mask = np.zeros(n_points, dtype=bool)
    is_efficient_mask[is_efficient] = True
    return is_efficient_mask


#def setup_output_files(logdir, output_file):
    """
    Writes the main output file header and returns the reward, hall of fame, and Pareto front config filenames.

    Parameters:
    -----------

    logdir : string
        Directory to log to.

    output_file : string
        Name of output file.

    Returns:
    --------

    all_r_output_file : str
        all_r output filename

    hof_output_file : str
        hof output filename

    pf_output_file : str
        pf output filename

    positional_entropy_output_file : str
        positional entropy filename

    cache_output_file : str
        cache output filename
    """
#    os.makedirs(logdir, exist_ok=True)
#    output_file = os.path.join(logdir, output_file)
#    prefix, _ = os.path.splitext(output_file)
#    all_r_output_file = "{}_all_r.npy".format(prefix)
#    hof_output_file = "{}_hof.csv".format(prefix)
#    pf_output_file = "{}_pf.csv".format(prefix)
#    positional_entropy_output_file = "{}_positional_entropy.npy".format(prefix)
#    cache_output_file = "{}_cache.csv".format(prefix)
#    with open(output_file, 'w') as f:
        # r_best : Maximum across all iterations so far
        # r_max : Maximum across this iteration's batch
        # r_avg_full : Average across this iteration's full batch (before taking epsilon subset)
        # r_avg_sub : Average across this iteration's epsilon-subset batch
        # n_unique_* : Number of unique Programs in batch
        # n_novel_* : Number of never-before-seen Programs per batch
        # a_ent_* : Empirical positional entropy across sequences averaged over positions
        # invalid_avg_* : Fraction of invalid Programs per batch
#        headers = ["base_r_best",
#                     "base_r_max",
#                     "base_r_avg_full",
#                     "base_r_avg_sub",
#                     "r_best",
#                     "r_max",
#                     "r_avg_full",
#                     "r_avg_sub",
#                     "l_avg_full",
#                     "l_avg_sub",
#                     "ewma",
#                     "n_unique_full",
#                     "n_unique_sub",
#                     "n_novel_full",
#                     "n_novel_sub",
#                     "a_ent_full",
#                     "a_ent_sub",
#                     "invalid_avg_full",
#                     "invalid_avg_sub"]
#         f.write("{}\n".format(",".join(headers)))
#
#     return all_r_output_file, hof_output_file, pf_output_file, positional_entropy_output_file, cache_output_file


class cached_property(object):
    """
    Decorator used for lazy evaluation of an object attribute. The property
    should be non-mutable, since it replaces itself.
    """

    def __init__(self, getter):
        self.getter = getter

        functools.update_wrapper(self, getter)

    def __get__(self, obj, cls):
        if obj is None:
            return self

        value = self.getter(obj)
        setattr(obj, self.getter.__name__, value)
        return value


def weighted_quantile(values, weights, q):
    """
    Computes the weighted quantile, equivalent to the exact quantile of the
    empirical distribution.

    Given ordered samples x_1 <= ... <= x_n, with corresponding weights w_1,
    ..., w_n, where sum_i(w_i) = 1.0, the weighted quantile is the minimum x_i
    for which the cumulative sum up to x_i is greater than or equal to 1.

    Quantile = min{ x_i | x_1 + ... + x_i >= q }
    """

    sorted_indices = np.argsort(values)
    sorted_weights = weights[sorted_indices]
    sorted_values = values[sorted_indices]
    cum_sorted_weights = np.cumsum(sorted_weights)
    i_quantile = np.argmax(cum_sorted_weights >= q)
    quantile = sorted_values[i_quantile]

    # NOTE: This implementation is equivalent to (but much faster than) the
    # following:
    # from scipy import stats
    # empirical_dist = stats.rv_discrete(name='empirical_dist', values=(values, weights))
    # quantile = empirical_dist.ppf(q)

    return quantile



# Entropy computation in batch
def empirical_entropy(labels):

    n_labels = len(labels)

    if n_labels <= 1:
        return 0

    value,counts = np.unique(labels, return_counts=True)
    probs = counts / n_labels
    n_classes = np.count_nonzero(probs)

    if n_classes <= 1:
        return 0

    ent = 0.
    # Compute entropy
    for i in probs:
        ent -= i * np.log(i)

    return ent

def get_duration(start_time):
    return get_human_readable_time(time.time() - start_time)

def get_human_readable_time(s):
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    return "{:02d}:{:02d}:{:02d}:{:05.2f}".format(int(d), int(h), int(m), s)

def safe_merge_dicts(base_dict, update_dict):
    """Merges two dictionaries without changing the source dictionaries.

    Parameters
    ----------
        base_dict : dict
            Source dictionary with initial values.
        update_dict : dict
            Dictionary with changed values to update the base dictionary.

    Returns
    -------
        new_dict : dict
            Dictionary containing values from the merged dictionaries.
    """
    if base_dict is None:
        return update_dict
    base_dict = copy.deepcopy(base_dict)
    for key, value in update_dict.items():
        if isinstance(value, collections.Mapping):
            base_dict[key] = safe_merge_dicts(base_dict.get(key, {}), value)
        else:
            base_dict[key] = value
    return base_dict