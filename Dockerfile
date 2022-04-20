FROM python:3.7

ENV PYTHONUNBUFFERED 1

RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y \
        git \
        libpq-dev \
        postgresql-client \
        libdb-dev \
        fp-compiler fp-units-base fp-units-math \
        texlive-latex-base \
        texlive-lang-polish \
        texlive-latex-extra \
        texlive-lang-german \
        texlive-lang-european \
        texlive-lang-czechslovak \
        texlive-pstricks \
        ghostscript \
        texlive-fonts-recommended \
        gcc-multilib \
        sudo \
        libstdc++6:i386 \
        zlib1g:i386 \
        locales \
        python3-pip && \
    apt-get clean

# This is oioioi user linux uid. Setting it is useful in development.
# By default we use an unused uid of 1234.
# This is placed here to avoid redownloading package on uid change
ARG oioioi_uid=1234

#Bash as shell, setup folders, create oioioi user
RUN rm /bin/sh && ln -s /bin/bash /bin/sh && \
    mkdir -pv /sio2/oioioi && \
    mkdir -pv /sio2/sandboxes && \
    useradd -U oioioi -m -d /home/oioioi/ -u $oioioi_uid && \
    echo "oioioi ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers && \
    chown -R oioioi:oioioi /sio2

# Modify locale
RUN sed -i -e "s/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/" /etc/locale.gen && \
    locale-gen

COPY ./entrypoint_checks.sh /entrypoint_checks.sh
RUN chmod +x /entrypoint_checks.sh && chown oioioi /entrypoint_checks.sh

# Installing python dependencies
USER oioioi

ENV PATH $PATH:/home/oioioi/.local/bin/

RUN pip3 install --user psycopg2-binary==2.8.6 twisted uwsgi

WORKDIR /sio2/oioioi

COPY --chown=oioioi:oioioi setup.py requirements.txt ./
RUN pip3 install -r requirements.txt --user
COPY --chown=oioioi:oioioi requirements_static.txt ./
RUN pip3 install -r requirements_static.txt --user

COPY --chown=oioioi:oioioi . /sio2/oioioi

RUN oioioi-create-config /sio2/deployment

WORKDIR /sio2/deployment

RUN sed -i -e \
       "s/SERVER = 'django'/SERVER = 'uwsgi-http'/g;\
        s/DEBUG = True/DEBUG = False/g;\
        s/django.db.backends./django.db.backends.postgresql/g;\
        s/'NAME': ''/'NAME': 'oioioi'/g;\
        s/'USER': ''/'USER': 'oioioi'/g;\
        s/'HOST': '',/'HOST': 'db',/g;\
        s/'PASSWORD': ''/'PASSWORD': 'password'/g;\
        s/#BROKER_URL/BROKER_URL/g;\
        s/#FILETRACKER_LISTEN_ADDR/FILETRACKER_LISTEN_ADDR/g;\
        s/#FILETRACKER_LISTEN_PORT/FILETRACKER_LISTEN_PORT/g;\
        s|#FILETRACKER_URL = '.*'|FILETRACKER_URL = 'http://web:9999'|g;\
        s/#RUN_SIOWORKERSD$/RUN_SIOWORKERSD/g;\
        s/#SIOWORKERS_LISTEN_ADDR/SIOWORKERS_LISTEN_ADDR/g;\
        s/#SIOWORKERS_LISTEN_PORT/SIOWORKERS_LISTEN_PORT/g;\
        s/RUN_LOCAL_WORKERS = True/RUN_LOCAL_WORKERS = False/g;\
        s/AVAILABLE_COMPILERS = SYSTEM_COMPILERS/#AVAILABLE_COMPILERS = SYSTEM_COMPILERS/g;\
        s/DEFAULT_COMPILERS = SYSTEM_DEFAULT_COMPILERS/#DEFAULT_COMPILERS = SYSTEM_DEFAULT_COMPILERS/g;\
        s/USE_UNSAFE_EXEC = True/USE_UNSAFE_EXEC = True/g;\
        s/#DEFAULT_SAFE_EXECUTION_MODE/#DEFAULT_SAFE_EXECUTION_MODE/g;\
        s/#USE_UNSAFE_CHECKER = True/#USE_UNSAFE_CHECKER = False/g;\
        \$afrom basic_settings import *\nALLOWED_HOSTS = ALLOWED_HOSTS + \\['oioioi', '127.0.0.1', 'localhost', 'web'\\]" \
        settings.py && \
    cp /sio2/oioioi/oioioi/selenium_settings.py selenium_settings.py && \
    mkdir -p /sio2/deployment/logs/{supervisor,runserver}

# Download sandboxes
RUN ./manage.py supervisor > /dev/null --daemonize --nolaunch=uwsgi && \
    ./manage.py download_sandboxes -q -y -c /sio2/sandboxes && \
    ./manage.py supervisor stop all
