def get_tag_prefix(tag):
    """This function returns the type of a tag, used for colors and searching"""

    prefixes = {
        'OriginTag': 'origin',
        'OriginInfoValue': 'origin',
        'AlgorithmTag': 'algorithm',
        'DifficultyTag': 'difficulty',
    }

    return prefixes[tag.__class__.__name__]
