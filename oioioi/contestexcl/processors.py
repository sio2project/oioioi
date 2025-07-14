def register_contest_exclusive(request):
    """A template context processor which adds information whether the current
    contest is exclusive to the templates.

    It is added to the template context as a ``contest_exclusive`` variable.
    """
    return {"contest_exclusive": getattr(request, "contest_exclusive", False)}
