def get_public_message(request, model, controller_default_attribute=None):
    if controller_default_attribute is None:
        controller_default_attribute = ''
    contest = request.contest
    if not model.objects.filter(contest=contest).exists():
        content = getattr(contest.controller, controller_default_attribute, '')
        model.objects.create(contest=contest, content=content)
    return model.objects.get(contest=contest)
