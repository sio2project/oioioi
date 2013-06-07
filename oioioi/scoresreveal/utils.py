from oioioi.scoresreveal.models import ScoreRevealConfig, ScoreReveal


def has_scores_reveal(problem):
    try:
        return bool(problem.scores_reveal_config)
    except ScoreRevealConfig.DoesNotExist:
        return False


def is_revealed(submission):
    try:
        return bool(submission.revealed)
    except ScoreReveal.DoesNotExist:
        return False
