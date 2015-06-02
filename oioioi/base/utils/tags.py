def get_tag_colors(tag):
    """This function decides how to color a certain tag.

       For a given tag name (as a string),
       it returns a tuple of strings (background color, text color).
       For example, get_tag_colors('swag') may return ('#bac010', '#1e48c0').

       It computes the background color basing on the tag name's hash.
       The text color is matched to the background color so that
       it will look as nice as it is possible on this background.
    """
    color = hash(tag) % (256 * 256 * 256)
    colors = [((color // 256**i) % 256) for i in (0, 1, 2)]
    if sum(colors) > 128 * 3:
        textcolors = (0, 0, 0)
    else:
        textcolors = (255, 255, 255)
    return ('#' + ''.join('%02x' % i for i in colors),
            '#' + ''.join('%02x' % i for i in textcolors))
