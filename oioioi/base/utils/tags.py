def get_tag_colors(tag):
    """This function decides how to color a certain tag based on its type"""

    colors = {
        'OriginTag': ('#C3A877', '#000000'),
        'AlgorithmTag': ('#2A2C59', '#ffffff'),
        'DifficultyTag': ('#2DB941', '#ffffff'),
        'Tag': ('#718D87', '#ffffff')
    }

    return colors[tag.__class__.__name__]
