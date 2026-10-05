from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter


def contest_id_parameter(extra_description=None, sep="\n\n", examples=None):
    description = (
        "The list of available contest ids can be retrieved through the contest_list endpoint. "
        "The Id of a specific contest can obtained from the web interface, it is "
        " the same as the contest name found after /c/ in the URL. For example, for "
        ' "/c/example-contest/dashboard/", the Id would be "example-contest".'
    )
    if extra_description is not None:
        description = extra_description + sep + description
    params = {
        "name": "contest_id",
        "type": OpenApiTypes.STR,
        "location": OpenApiParameter.PATH,
        "description": description,
    }
    if examples is not None:
        params["examples"] = examples
    return OpenApiParameter(**params)
