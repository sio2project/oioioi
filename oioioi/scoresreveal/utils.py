from oioioi.scoresreveal.models import ScoreReveal, ScoreRevealConfig


def has_scores_reveal(problem_instance):
    try:
        return bool(problem_instance.scores_reveal_config)
    except ScoreRevealConfig.DoesNotExist:
        return False


def is_revealed(submission):
    try:
        return bool(submission.revealed)
    except ScoreReveal.DoesNotExist:
        return False
