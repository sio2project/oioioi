FROM python:3.10

ENV PYTHONUNBUFFERED 1
ENV YES_I_HAVE_THE_RIGHT_TO_USE_THIS_BERKELEY_DB_VERSION 1

#RUN dpkg --add-architecture i386
RUN apt-get update && \
    apt-get install -y \
        nginx \
        proot \
        git \
        libpq-dev \
        postgresql-client \
        libdb-dev \
        texlive-latex-base \
        texlive-lang-polish \
        texlive-latex-extra \
        texlive-lang-german \
        texlive-lang-european \
        texlive-lang-czechslovak \
        texlive-pstricks \
        ghostscript \
        texlive-fonts-recommended \
        gcc \
        sudo \
        libstdc++6 \
        zlib1g \
        locales \
        sox \
        flite \
        nodejs \
        npm \
        python3-pip && \
    apt-get clean

# This is oioioi user linux uid. Setting it is useful in development.
# By default we use an unused uid of 1234.
# This is placed here to avoid redownloading package on uid change
ARG oioioi_uid=1234

#Bash as shell, setup folders, create oioioi user, modify locale
RUN rm /bin/sh && ln -s /bin/bash /bin/sh && \
    mkdir -pv /sio2/oioioi /sio2/sandboxes && \
    useradd -U oioioi -m -d /home/oioioi/ -u $oioioi_uid && \
    echo "oioioi ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers && \
    chown -R oioioi:oioioi /sio2 && \
    sed -i -e "s/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/" /etc/locale.gen && \
    locale-gen

COPY --chmod=+x --chown=oioioi ./entrypoint_checks.sh /entrypoint_checks.sh
# RUN chmod +x /entrypoint_checks.sh && chown oioioi /entrypoint_checks.sh
# export DOCKER_BUILDKIT=1

# Installing python dependencies
USER oioioi

ENV PATH $PATH:/home/oioioi/.local/bin/

RUN pip3 install --user psycopg2-binary==2.8.6 twisted uwsgi
RUN pip3 install --user bsddb3==6.2.7

WORKDIR /sio2/oioioi

COPY --chown=oioioi:oioioi setup.py requirements.txt ./
RUN pip3 install -r requirements.txt --user && \
    pip3 cache purge
COPY --chown=oioioi:oioioi requirements_static.txt ./
RUN pip3 install -r requirements_static.txt --user && \
    pip3 cache purge

COPY --chown=oioioi:oioioi . /sio2/oioioi


ENV OIOIOI_DB_ENGINE 'django.db.backends.postgresql'
ENV RABBITMQ_HOST 'broker'
ENV RABBITMQ_PORT '5672'
ENV RABBITMQ_USER 'oioioi'
ENV RABBITMQ_PASSWORD 'oioioi'
ENV FILETRACKER_LISTEN_ADDR '0.0.0.0'
ENV FILETRACKER_LISTEN_PORT '9999'
ENV FILETRACKER_URL 'http://web:9999'
ENV SIOWORKERS_SANDBOXES_URL https://otsrv.net/sandboxes/

RUN oioioi-create-config /sio2/deployment && \
    echo "from basic_settings import *" >> /sio2/deployment/settings.py

WORKDIR /sio2/deployment

RUN mkdir -p /sio2/deployment/{sockets,logs/{supervisor,runserver}} && \
    sudo ln -fs /sio2/deployment/nginx-site.conf /etc/nginx/sites-available/default

# Download sandboxes
RUN ./manage.py supervisor > /dev/null --daemonize --nolaunch=uwsgi \
        --nolaunch=rankingsd --nolaunch=mailnotifyd --nolaunch=evalmgr \
        --nolaunch=unpackmgr --nolaunch=sioworkersd \
        --nolaunch=receive_from_workers --nolaunch=notifications-server && \
    ./manage.py download_sandboxes -q -y -c /sio2/sandboxes && \
    ./manage.py supervisor stop all && \
    rm -rf /sio2/deployment/cache
