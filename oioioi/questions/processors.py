from django.template import Template, Context
from django.core.urlresolvers import reverse
from django.utils.translation import ungettext
from django.utils.functional import lazy
from oioioi.base.utils import make_navbar_badge
from oioioi.questions.views import new_messages, visible_messages

def navbar_tip_processor(request):
    if not getattr(request, 'contest', None):
        return {}
    if not request.user.is_authenticated():
        return {}
    def generator():
        is_admin = request.user.has_perm('contests.contest_admin',
                request.contest)
        messages = visible_messages(request)
        if is_admin:
            messages = messages.filter(message__isnull=True,
                    top_reference__isnull=True, kind='QUESTION')
        else:
            messages = new_messages(request, messages)
        count = messages.count()
        if count:
            text = ungettext('%(count)d NEW MESSAGE', '%(count)d NEW MESSAGES',
                    count) % {'count': count}
            if count == 1:
                message = messages.get()
                link = reverse('message', kwargs={
                        'contest_id': request.contest.id,
                        'message_id': message.top_reference_id or message.id
                    })
            else:
                link = reverse('contest_messages', kwargs={'contest_id':
                    request.contest.id})
            return make_navbar_badge(link, text)
        else:
            return ''
    return {'extra_navbar_right_messages': lazy(generator, unicode)()}

