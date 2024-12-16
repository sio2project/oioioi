def get_tag_prefix(tag):
    """Return the type of a tag, used for colors and searching."""

    prefixes = {
        'OriginTag': 'origin',
        'OriginInfoValue': 'origin',
        'AlgorithmTag': 'algorithm',
        'DifficultyTag': 'difficulty',
        'AlgorithmTagProposal': 'algorithm-proposal',
        'DifficultyTagProposal': 'difficulty-proposal',
        'AggregatedAlgorithmTagProposal': 'algorithm-proposal',
        'AggregatedDifficultyTagProposal': 'difficulty-proposal',
    }

    return prefixes[tag.__class__.__name__]


def get_tag_name(tag):
    """Return the name of a tag to display, used for colors and searching."""

    prefixes = {
        'OriginTag': tag.name,
        'OriginInfoValue': tag.name,
        'AlgorithmTag': tag.name,
        'DifficultyTag': tag.full_name,
    }

    return prefixes[tag.__class__.__name__]
