def get_public_message(request, model, controller_default_value=None):
    if controller_default_value is None:
        controller_default_value = ''
    contest = request.contest
    if not model.objects.filter(contest=contest).exists():
        content = getattr(contest.controller, controller_default_value, '')
        model.objects.create(contest=contest, content=content)
    return model.objects.get(contest=contest)
