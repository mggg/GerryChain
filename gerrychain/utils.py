from collections import defaultdict


def level_sets(mapping: dict, container=set):
    """Inverts a dictionary. ``{key: value}`` becomes
    ``{value: <container of keys that map to value>}``."""
    sets = defaultdict(container)
    for source, target in mapping.items():
        sets[target].add(source)
    return sets
