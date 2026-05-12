def get_public_message(request, model, controller_default_attribute=None):
    if controller_default_attribute is None:
        controller_default_attribute = ""
    if not hasattr(request, "contest") or request.contest is None:
        return None
    contest = request.contest
    message = model.objects.filter(contest=contest).first()
    if not message:
        content = getattr(contest.controller, controller_default_attribute, "")
        message = model.objects.create(contest=contest, content=content)
    return message
