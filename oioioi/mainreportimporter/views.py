# -.- coding: utf-8 -.-

from django.conf import settings
from django.template.response import TemplateResponse
from django.contrib import messages
from django.shortcuts import redirect
from requests.exceptions import ConnectionError

import requests

from oioioi.problems.problem_site import problem_site_tab

SAVE_REPORT_ORDER_PATH = '/var/lib/sio2/deployment/import_reports/orders'

def import_report_view(request, problem=None):
    if request.method == 'POST':
        login = request.POST['login']
        password = request.POST['password']

        try:
            r = requests.post('http://main/en/login',
                    data={'auth': 1, 'login':login, 'pass':password})
            if r.status_code != 200:
                messages.error(request, 'Błąd przy łączeniu z main.edu.pl (%d)' % (request.status_code,))
            if 'Bad login or password' in r.content:
                messages.error(request, "Niepoprawny login lub hasło")
            else:
                messages.success(request, "Udane logowanie")
                order = {}
                order['user'] = request.user.id
                order['main-username'] = login
                filename = "order_" + str(request.user.id)
                if problem:
                    order['tags'] = [tag.name for tag in problem.tag_set.all()]
                    order['problem_id'] = problem.id
                    filename += "_" + str(problem.id)
                f = open(SAVE_REPORT_ORDER_PATH + filename, 'w')
                f.write(str(order))
                f.close()

                return redirect('import_report_success')
        except ConnectionError:
            messages.error(request, 'Błąd przy łączeniu z main.edu.pl')

    template = 'mainreportimporter/import_all.html'
    if problem is not None:
        template = 'mainreportimporter/import_problem.html'
    return TemplateResponse(request, template,
            context={'problem': problem})


@problem_site_tab(u"import z MAIN / import from MAIN", key='import_report', order=2072)
def import_report_problemsite_view(request, problem):
    print problem
    return import_report_view(request, problem)


def import_report_success_view(request):
    return TemplateResponse(request, 'mainreportimporter/success.html')

