def narrow_input_field(field):
    """Marks form input field to be marked as narrow"""
    try:
        field.widget.attrs['class'] += ' oioioi-narrow-input'
    except KeyError:
        field.widget.attrs['class'] = 'oioioi-narrow-input'


def narrow_input_fields(fields):
    """Marks form input fields to be marked as narrow"""
    for field in fields:
        narrow_input_field(field)
