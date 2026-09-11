from oioioi.scoresreveal.models import ScoreReveal


# Django doesn't cache a lack of the related object, so we do it manually.
def get_scores_reveal_config_universal(obj):
    key = "_scores_reveal_config_cache"
    if not hasattr(obj, key):
        setattr(obj, key, getattr(obj, "scores_reveal_config", None))
    return getattr(obj, key)


def get_scores_reveal_config_for_problem_instance(problem_instance):
    pi_config = get_scores_reveal_config_universal(problem_instance)
    if pi_config is not None:
        return pi_config

    if problem_instance.contest_id is None:
        return None
    # This performs well for many problem instances if the contest object is shared across
    # them (e.g. in problem list view), so prefetch_related or annotate_known_related for
    # the contest are needed in such places.
    return get_scores_reveal_config_universal(problem_instance.contest)


def has_scores_reveal(problem_instance):
    scores_reveal_config = get_scores_reveal_config_for_problem_instance(problem_instance)
    if scores_reveal_config is None:
        return False
    reveal_limit = scores_reveal_config.reveal_limit
    # None means auto-reveal.
    return reveal_limit is None or reveal_limit > 0


def is_revealed(submission):
    try:
        return bool(submission.revealed)
    except ScoreReveal.DoesNotExist:
        return False
