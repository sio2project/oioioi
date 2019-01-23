FROM python:2.7

ENV PYTHONUNBUFFERED 1

RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y \
        git \
        libpq-dev \
        postgresql-client \
        rabbitmq-server \
        libdb-dev \
        fp-compiler fp-units-base fp-units-math \
        texlive-latex-base \
        texlive-lang-polish \
        texlive-latex-extra \
        texlive-fonts-recommended \
        gcc-multilib \
        sudo \
        libstdc++6:i386 \
        zlib1g:i386 \
        locales && \
    apt-get clean

# This is oioioi user linux uid. Setting it is useful in development.
# By default we use an unused uid of 1234.
# This is placed here to avoid redownloading package on uid change
ARG oioioi_uid=1234

#Bash as shell, setup folders, create oioioi user
RUN rm /bin/sh && ln -s /bin/bash /bin/sh && \
    mkdir -pv /sio2/oioioi && \
    mkdir -pv /sio2/logs && \
    mkdir -pv /sio2/sandboxes && \
    chmod a+rw -R /sio2/logs && \
    useradd -U oioioi -m -d /home/oioioi/ -u $oioioi_uid && \
    echo "oioioi ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers && \
    chown -R oioioi:oioioi /sio2

# Modify locale
RUN sed -i -e "s/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/" /etc/locale.gen && \
    locale-gen

# Configure rabbitmq-server
RUN echo "[{rabbit, [{tcp_listeners, [5672]}, {loopback_users, []}]}]." > /etc/rabbitmq/rabbitmq.config && \
    echo "SERVER_ERL_ARGS=\"+K true +A 4 +P 1048576 -kernel\""          > /etc/rabbitmq/rabbitmq-env.conf

# Configuring .bashrc
RUN echo "source /sio2/venv/bin/activate" >> ~/.bashrc && \
    echo "cd /sio2" >> ~/.bashrc && \
    echo "export PATH=$PATH:~/.local/bin" >> ~/.bashrc

# Installing python dependencies
USER oioioi

RUN easy_install --user distribute
RUN pip install psycopg2-binary --user
RUN pip install twisted --user

WORKDIR /sio2/oioioi

COPY setup.py requirements.txt ./
RUN pip install -r requirements.txt --user

ADD --chown=oioioi:oioioi . /sio2/oioioi

ENV PATH $PATH:/home/oioioi/.local/bin/

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
        s/#FILETRACKER_URL/FILETRACKER_URL/g;\
        s/#SIOWORKERS_LISTEN_ADDR/SIOWORKERS_LISTEN_ADDR/g;\
        s/#SIOWORKERS_LISTEN_PORT/SIOWORKERS_LISTEN_PORT/g;\
        s/#RUN_SIOWORKERSD.*$/RUN_SIOWORKERSD = True/g;\
        s/#USE_UNSAFE_EXEC = True/USE_UNSAFE_EXEC = True/g;\
        s/#USE_LOCAL_COMPILERS = True/USE_LOCAL_COMPILERS = False/g;\
        s/#USE_UNSAFE_CHECKER = True/USE_UNSAFE_CHECKER = False/g;\
        s/.*RUN_LOCAL_WORKERS = True/RUN_LOCAL_WORKERS = False/g;\
        s/ALLOWED_HOSTS = \\[.*\\]/ALLOWED_HOSTS = \\['oioioi', '127.0.0.1', 'localhost', 'web'\\]/g"\
        settings.py && \
    echo "SIOWORKERS_BACKEND = 'oioioi.sioworkers.backends.SioworkersdBackend'"     >> settings.py && \
    echo "CELERY_RESULT_BACKEND = None"                                             >> settings.py && \
    sed -i \
        -e "s|twistd|/home/oioioi/.local/bin/twistd|g"\
        -e "s|{{ PROJECT_DIR }}/logs|/sio2/logs|g"\
        -e "s|command=filetracker-server|command=/home/oioioi/.local/bin/filetracker-server|g"\
        supervisord.conf && \
    mkdir -p /sio2/logs/{supervisor,runserver}

# Download sandboxes
RUN ./manage.py supervisor > /dev/null --daemonize && \
    ./manage.py download_sandboxes -q -y -c /sio2/sandboxes && \
    ./manage.py supervisor stop all

RUN sed -i -e "s|FILETRACKER_URL = '.*'|FILETRACKER_URL = 'http://web:9999'|g" settings.py && \
    cp settings.py test_settings.py && \
    sed -i -e "s/from oioioi.default_settings/from oioioi.test_settings/g" test_settings.py && \
    cp settings.py selenium_settings.py && \
    sed -i -e "s/from oioioi.default_settings/from oioioi.selenium_settings/g" selenium_settings.py
