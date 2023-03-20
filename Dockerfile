# This is oioioi user linux uid. Setting it is useful in development.
# By default we use an unused uid of 1234.
# This is placed here to avoid redownloading package on uid change
ARG OIOIOI_UID=1234

FROM python:3.7 AS build

ENV PYTHONUNBUFFERED 1

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
        git \
        libpq-dev \
        libdb5.3-dev

ARG OIOIOI_UID

RUN useradd -u ${OIOIOI_UID} -m oioioi \
    && mkdir -p /sio2/oioioi \
    && chown -R oioioi:oioioi /sio2

USER oioioi
WORKDIR /sio2

RUN pip install --user virtualenv \
    && /home/oioioi/.local/bin/virtualenv -p python3.7 venv

RUN . /sio2/venv/bin/activate \
    && pip install psycopg2-binary==2.8.6 twisted librabbitmq uwsgi

COPY --chown=oioioi:oioioi setup.py requirements.txt /sio2/oioioi/

WORKDIR /sio2/oioioi

RUN . /sio2/venv/bin/activate \
    && pip install -r requirements.txt

COPY --chown=oioioi:oioioi . /sio2/oioioi

FROM python:3.7 AS base

ENV PYTHONUNBUFFERED 1

RUN dpkg --add-architecture i386 \
    && apt-get update \
    && apt-get install -y \
        sudo \
        wget \
        locales \
        libdb5.3 \
        postgresql-client \
        texlive-latex-base \
        texlive-lang-polish \
        texlive-latex-extra \
        texlive-lang-german \
        texlive-lang-european \
        texlive-lang-czechslovak \
        texlive-pstricks \
        texlive-fonts-recommended \
        ghostscript \
        flite \
        sox \
        libstdc++6:i386 \
        zlib1g:i386 \
    && rm -rf /var/lib/apt/lists/*

ARG OIOIOI_UID

RUN useradd -u ${OIOIOI_UID} -m oioioi \
    && mkdir -p /sio2/oioioi \
    && chown -R oioioi:oioioi /sio2 \
    && echo "oioioi ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Modify locale
RUN sed -i -e "s/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/" /etc/locale.gen \
    && locale-gen

USER oioioi

COPY --from=build --chown=oioioi:oioioi /sio2 /sio2

WORKDIR /sio2

RUN . /sio2/venv/bin/activate \
    && oioioi-create-config --docker deployment

WORKDIR /sio2/deployment

RUN sed -i -e \
        "s/#FILETRACKER_LISTEN_ADDR/FILETRACKER_LISTEN_ADDR/g;\
        s/#FILETRACKER_LISTEN_PORT/FILETRACKER_LISTEN_PORT/g;\
        s/#RUN_SIOWORKERSD$/RUN_SIOWORKERSD/g;\
        s/AVAILABLE_COMPILERS = SYSTEM_COMPILERS/#AVAILABLE_COMPILERS = SYSTEM_COMPILERS/g;\
        s/DEFAULT_COMPILERS = SYSTEM_DEFAULT_COMPILERS/#DEFAULT_COMPILERS = SYSTEM_DEFAULT_COMPILERS/g;\
        \$afrom basic_settings import *" \
        settings.py && \
    mkdir -p /sio2/deployment/logs/{supervisor,runserver}

FROM base AS development

USER root

RUN apt-get update \
    && apt-get install -y \
        fp-compiler \
        fp-units-base \
        fp-units-math \
        gcc-multilib \
    && rm -rf /var/lib/apt/lists/*

USER oioioi

WORKDIR /sio2/oioioi

COPY --chown=oioioi:oioioi requirements_static.txt /sio2/oioioi
RUN . /sio2/venv/bin/activate \
    && pip install -r requirements_static.txt

RUN cp /sio2/oioioi/oioioi/selenium_settings.py /sio2/deployment/selenium_settings.py

WORKDIR /sio2/deployment

ENTRYPOINT [ "/sio2/oioioi/scripts/docker-entrypoint.sh" ]

FROM base as production

WORKDIR /sio2/deployment

ENTRYPOINT [ "/sio2/oioioi/scripts/docker-entrypoint.sh" ]
