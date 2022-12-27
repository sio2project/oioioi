from oioioi.scoresreveal.models import ScoreReveal, ScoreRevealConfig, ScoreRevealContestConfig


def has_scores_reveal(problem_instance):
    try:
        return bool(problem_instance.scores_reveal_config)
    except ScoreRevealConfig.DoesNotExist:
        try:
            return bool(problem_instance.contest.scores_reveal_config)
        except ScoreRevealContestConfig.DoesNotExist:
            return False


def is_revealed(submission):
    try:
        return bool(submission.revealed)
    except ScoreReveal.DoesNotExist:
        return False
