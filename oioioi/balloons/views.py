from django.utils.translation import ugettext_lazy as _
from django.template.response import TemplateResponse
from django.http import Http404
from oioioi.contests.models import UserResultForProblem
from oioioi.contests.utils import can_enter_contest
from oioioi.balloons.models import BalloonsDisplay


def balloons_context(user, list_of_colors):
    if len(list_of_colors) <= 1:
        step = 0
    else:
        step = 60 / (len(list_of_colors) - 1)
    balloons = [{
            'color': c[1:],
            'left': 20 + i * step,
        } for i, c in enumerate(list_of_colors)]
    return {'balloons_user': user, 'balloons': balloons}


def query_context_args(user, contest):
    return UserResultForProblem.objects\
            .filter(problem_instance__contest=contest, user=user, status='OK',
                    problem_instance__balloons_config__color__isnull=False) \
            .order_by('submission_report__submission__date') \
            .values_list('problem_instance__balloons_config__color', flat=True)


def context_args(request):
    if request.user.is_authenticated() and can_enter_contest(request) \
            and request.contest is not None:
        return request.user, query_context_args(request.user, request.contest)
    ip_addr = request.META.get('REMOTE_ADDR')
    if not ip_addr:
        raise Http404(_("No IP address detected"))
    try:
        display = BalloonsDisplay.objects.get(ip_addr=ip_addr)
    except BalloonsDisplay.DoesNotExist:
        raise Http404(_("No balloons display configured for this IP: %s")
            % (ip_addr,))
    return display.user, query_context_args(display.user, display.contest)


def balloon_svg_view(request, color):
    return TemplateResponse(request, 'balloons/balloon.svg',
            {'color': '#' + color}, content_type='image/svg+xml')


def balloons_view(request):
    args = context_args(request)
    return TemplateResponse(request, 'balloons/balloons.html',
        balloons_context(*args))


def balloons_body_view(request):
    args = context_args(request)
    return TemplateResponse(request, 'balloons/balloons-body.html',
        balloons_context(*args))
