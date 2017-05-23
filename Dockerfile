FROM oioioi-base

RUN rm /bin/sh && ln -s /bin/bash /bin/sh

# Setup directories
RUN mkdir -pv /sio2/oioioi
RUN mkdir -pv /sio2/logs/
RUN chmod a+rw -R /sio2/logs

# Create users and set permissions
RUN useradd -U oioioi -m -d /home/oioioi/
RUN adduser oioioi sudo
ADD . /sio2/oioioi
RUN chown -R oioioi /sio2
RUN echo "oioioi ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Modify locale
RUN sed -i -e "s/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/" /etc/locale.gen
RUN locale-gen


# Configure rabbitmq-server
RUN echo "[{rabbit, [{tcp_listeners, [5672]}, {loopback_users, []}]}]." > /etc/rabbitmq/rabbitmq.config
RUN echo "SERVER_ERL_ARGS=\"+K true +A 4 +P 1048576 -kernel\""          > /etc/rabbitmq/rabbitmq-env.conf


# Configuring .bashrc
RUN echo "source /sio2/venv/bin/activate" >> ~/.bashrc
RUN echo "cd /sio2" >> ~/.bashrc
RUN echo "export PATH=$PATH:~/.local/bin" >> ~/.bashrc

# Installing python dependencies
USER oioioi

WORKDIR /sio2/oioioi
RUN easy_install --user distribute
RUN pip install -r requirements.txt --user
RUN pip install psycopg2 --user
RUN pip install twisted --user

ENV PATH $PATH:~/.local/bin/

RUN oioioi-create-config /sio2/deployment

WORKDIR /sio2/deployment

RUN sed -i -e \
       "s/django.db.backends./django.db.backends.postgresql_psycopg2/g;\
        s/'NAME': ''/'NAME': 'oioioi'/g;\
        s/'USER': ''/'USER': 'oioioi'/g;\
        s/'HOST': '',/'HOST': 'db',/g;\
        s/'PASSWORD': ''/'PASSWORD': ''/g;\
        s/#BROKER_URL/BROKER_URL/g;\
        s/USE_UNSAFE_EXEC/#USE_UNSAFE_EXEC/g;\
        s/USE_LOCAL_COMPILERS/#USE_LOCAL_COMPILERS/g;\
        s/#FILETRACKER_SERVER_ENABLED/FILETRACKER_SERVER_ENABLED/g;\
        s/#FILETRACKER_LISTEN_ADDR/FILETRACKER_LISTEN_ADDR/g;\
        s/#FILETRACKER_LISTEN_PORT/FILETRACKER_LISTEN_PORT/g;\
        s/#FILETRACKER_LISTEN_URL/FILETRACKER_LISTEN_URL/g;\
        s|#FILETRACKER_URL = 'http://127.0.0.1:9999'|FILETRACKER_URL = 'http://web:9999'|g;\
        s/#SIOWORKERS_LISTEN_ADDR/SIOWORKERS_LISTEN_ADDR/g;\
        s/#SIOWORKERS_LISTEN_PORT/SIOWORKERS_LISTEN_PORT/g;\
        s/#RUN_SIOWORKERSD.*$/RUN_SIOWORKERSD = True/g;\
        s/#USE_UNSAFE_EXEC = True/USE_UNSAFE_EXEC = True/g;\
        s/#USE_LOCAL_COMPILERS = True/USE_LOCAL_COMPILERS = False/g;\
        s/#USE_UNSAFE_CHECKER = True/USE_UNSAFE_CHECKER = False/g;\
        s/.*RUN_LOCAL_WORKERS = True/RUN_LOCAL_WORKERS = False/g;\
        s/ALLOWED_HOSTS = \\[\\]/ALLOWED_HOSTS = \\['oioioi', '127.0.0.1', 'web'\\]/g"\
        -e "/INSTALLED_APPS =/a\
        'oioioi.contestlogo',\
        'oioioi.teachers',\
        'oioioi.ipdnsauth',\
        'oioioi.participants',\
        'oioioi.oi',\
        'oioioi.printing',\
        'oioioi.zeus',\
        'oioioi.testrun',\
        'oioioi.scoresreveal',\
        'oioioi.oireports',\
        'oioioi.oisubmit',\
        'oioioi.complaints',\
        'oioioi.contestexcl',\
        'oioioi.forum',\
        'oioioi.exportszu',\
        'oioioi.similarsubmits',\
        'oioioi.disqualification',\
        'oioioi.confirmations',\
        'oioioi.ctimes',\
        'oioioi.acm',\
        'oioioi.suspendjudge',\
        'oioioi.submitservice',\
        'oioioi.timeline',\
        'oioioi.statistics',\
        'oioioi.amppz',\
        'oioioi.balloons',\
        'oioioi.publicsolutions',\
        'oioioi.testspackages',\
        'oioioi.teams',\
        'oioioi.pa',\
        'oioioi.notifications',\
        'oioioi.prizes',\
        'oioioi.mailsubmit',\
        'oioioi.globalmessage',\
        'oioioi.portals',\
        'oioioi.workers',\
        'oioioi.newsfeed',\
        'oioioi.simpleui',\
        'oioioi.livedata',\
        "\
        settings.py

RUN echo "SIOWORKERS_BACKEND = 'oioioi.sioworkers.backends.SioworkersdBackend'"     >> settings.py
RUN echo "CELERY_RESULT_BACKEND = None"                                             >> settings.py

RUN sed -i \
        -e "s|twistd|/home/oioioi/.local/bin/twistd|g"\
        -e "s|{{ PROJECT_DIR }}/logs|/sio2/logs|g"\
        -e "s|command=filetracker-server|command=/home/oioioi/.local/bin/filetracker-server|g"\
        supervisord.conf
RUN mkdir /sio2/sandboxes
RUN ./manage.py download_sandboxes -q -y -c /sio2/sandboxes
