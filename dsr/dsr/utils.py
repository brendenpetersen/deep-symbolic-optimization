"""Utility functions used in deep symbolic regression."""

import heapq
import functools

import numpy as np

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


# Adapted from https://github.com/tensorflow/models/blob/1af55e018eebce03fb61bba9959a04672536107d/research/brain_coder/common/utils.py
class MPQItemContainer(object):
    """Class for holding an item with its score.

    Defines a comparison function for use in the heap-queue.
    """

    def __init__(self, score, item, extra_data):
        self.item = item
        self.score = score
        self.extra_data = extra_data


    def __lt__(self, other):
        assert isinstance(other, type(self))
        return self.score < other.score

    def __iter__(self):
        """Allows unpacking like a tuple."""
        yield self.score
        yield self.item
        yield self.extra_data

    def __repr__(self):
        """String representation of this item.

        `extra_data` is not included in the representation. We are assuming that
        `extra_data` is not easily interpreted by a human (if it was, it should be
        hashable, like a string or tuple).

        Returns:
            String representation of `self`.
        """
        return str((self.score, self.item))

    def __str__(self):
        return repr(self)


# Adapted from https://github.com/tensorflow/models/blob/1af55e018eebce03fb61bba9959a04672536107d/research/brain_coder/common/utils.py
class MaxUniquePriorityQueue(object):
    """A maximum priority queue where duplicates are not added.

    The top items by score remain in the queue. When the capacity is reached,
    the lowest scored item in the queue will be dropped.

    This implementation differs from a typical priority queue, in that the minimum
    score is popped, instead of the maximum. Largest scores remain stuck in the
    queue. This is useful for accumulating the best known items from a population.

    The items used to determine uniqueness must be hashable, but additional
    non-hashable data may be stored with each item.
    """

    def __init__(self, capacity, seed=0):
        self.capacity = capacity
        self.heap = []
        self.unique_items = set()
        self.rng = np.random.RandomState(seed)

    def push(self, score, item, extra_data=None):
        """Push an item onto the queue.

        If the queue is at capacity, the item with the smallest score will be
        dropped. Note that it is assumed each item has exactly one score. The same
        item with a different score will still be dropped.

        Args:
            score: Number used to prioritize items in the queue. Largest scores are
                    kept in the queue.
            item: A hashable item to be stored. Duplicates of this item will not be
                    added to the queue.
            extra_data: An extra (possible not hashable) data to store with the item.
        """
        if item in self.unique_items:
            return
        if len(self.heap) >= self.capacity:
            _, popped_item, _ = heapq.heappushpop(
                    self.heap, MPQItemContainer(score, item, extra_data))
            self.unique_items.add(item)
            self.unique_items.remove(popped_item)
        else:
            heapq.heappush(self.heap, MPQItemContainer(score, item, extra_data))
            self.unique_items.add(item)

    def pop(self):
        """Pop the item with the lowest score.

        Returns:
            score: Item's score.
            item: The item that was popped.
            extra_data: Any extra data stored with the item.
        """
        if not self.heap:
            return ()
        score, item, extra_data = heapq.heappop(self.heap)
        self.unique_items.remove(item)
        return score, item, extra_data

    def get_max(self):
        """Peek at the item with the highest score.

        Returns:
            Same as `pop`.
        """
        if not self.heap:
            return ()
        score, item, extra_data = heapq.nlargest(1, self.heap)[0]
        return score, item, extra_data

    def get_min(self):
        """Peek at the item with the lowest score.

        Returns:
            Same as `pop`.
        """
        if not self.heap:
            return ()
        score, item, extra_data = heapq.nsmallest(1, self.heap)[0]
        return score, item, extra_data

    def random_sample(self, sample_size):
        """Randomly select items from the queue.

        This does not modify the queue.

        Items are drawn from a uniform distribution, and not weighted by score.

        Args:
            sample_size: Number of random samples to draw. The same item can be
                    sampled multiple times.

        Returns:
            List of sampled items (of length `sample_size`). Each element in the list
            is a tuple: (item, extra_data).
        """
        idx = self.rng.choice(len(self.heap), sample_size, )
        return [(self.heap[i].item, self.heap[i].extra_data) for i in idx]

    def iter_in_order(self):
        """Iterate over items in the queue from largest score to smallest.

        Yields:
            item: Hashable item.
            extra_data: Extra data stored with the item.
        """
        for _, item, extra_data in heapq.nlargest(len(self.heap), self.heap):
            yield item, extra_data

    def __len__(self):
        return len(self.heap)

    def __iter__(self):
        for _, item, _ in self.heap:
            yield item

    def __repr__(self):
        return '[' + ', '.join(repr(c) for c in self.heap) + ']'

    def __str__(self):
        return repr(self)
