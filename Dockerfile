FROM python:3.8

ENV PYTHONUNBUFFERED 1

#RUN dpkg --add-architecture i386
RUN apt-get update && \
    apt-get install -y \
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
        sox \
        flite \
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

ENV BERKELEYDB_DIR /usr
RUN pip3 install --user psycopg2-binary==2.8.6 twisted uwsgi
RUN pip3 install --user bsddb3==6.2.7

WORKDIR /sio2/oioioi

COPY --chown=oioioi:oioioi setup.py requirements.txt ./
RUN pip3 install -r requirements.txt --user
COPY --chown=oioioi:oioioi requirements_static.txt ./
RUN pip3 install -r requirements_static.txt --user

COPY --chown=oioioi:oioioi . /sio2/oioioi


ENV OIOIOI_DB_ENGINE 'django.db.backends.postgresql'
ENV RABBITMQ_HOST 'broker'
ENV RABBITMQ_PORT '5672'
ENV RABBITMQ_USER 'oioioi'
ENV RABBITMQ_PASSWORD 'oioioi'
ENV FILETRACKER_LISTEN_ADDR '0.0.0.0'
ENV FILETRACKER_LISTEN_PORT '9999'
ENV FILETRACKER_URL 'http://web:9999'

RUN oioioi-create-config /sio2/deployment

WORKDIR /sio2/deployment

RUN mkdir -p /sio2/deployment/logs/{supervisor,runserver}

# Download sandboxes
RUN ./manage.py supervisor > /dev/null --daemonize --nolaunch=uwsgi && \
    ./manage.py download_sandboxes -q -y -c /sio2/sandboxes && \
    ./manage.py supervisor stop all
