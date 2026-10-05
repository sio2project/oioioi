from django.template import Library
from django.utils.html import format_html

register = Library()


@register.simple_tag
def ordered_col(GET, col_name, desc_default=False):
    # Preserve all unrelated GET parameters
    params = GET.dict()

    # Invert order if clicked again
    if params.get("order_by") == col_name:
        if "desc" in params:
            del params["desc"]
        else:
            params["desc"] = None
    else:
        params["order_by"] = col_name
        if desc_default:
            params["desc"] = None
        elif "desc" in params:
            del params["desc"]

    return format_html("?{}", "&".join((k + ("=" + v if v else "")) for k, v in params.items()))


@register.simple_tag
def prob_filter(GET, filter_name):
    # Preserve all unrelated GET parameters
    params = GET.dict()

    params["filter"] = filter_name

    return format_html("?{}", "&".join((k + ("=" + v if v else "")) for k, v in params.items()))
