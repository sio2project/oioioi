

def can_user_enter_round(request_or_context, round):
    # context is for rankings, it doesn't know about rounds, thus
    # filtering the visible ones will be relevant only for requests
    if not hasattr(request_or_context, 'is_under_supervision') or \
            request_or_context.user.is_superuser:
        return True
    id = getattr(round, 'id', None)
    if request_or_context.is_under_supervision:
        return id in request_or_context.supervision_visible_rounds
    return id not in request_or_context.supervision_hidden_rounds
