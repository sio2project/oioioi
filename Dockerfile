FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS base

ENV PYTHONUNBUFFERED=1

#RUN dpkg --add-architecture i386
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
        git \
        libpq-dev \
        postgresql-client \
        libdb-dev \
        libmemcached-dev \
        texlive-latex-base \
        texlive-lang-polish \
        texlive-latex-extra \
        texlive-lang-german \
        texlive-lang-european \
        texlive-lang-czechslovak \
        texlive-pstricks \
        texlive-fonts-recommended \
        tex-gyre \
        ghostscript \
        make \
        gcc \
        g++ \
        libc6-dev \
        sudo \
        libstdc++6 \
        zlib1g \
        sox \
        flite \
        locales \
        nodejs \
        npm && \
    apt-get clean && \
    rm -rf /usr/share/doc/texlive* && \
    npm install -g pnpm

# This is oioioi user linux uid. Setting it is useful in development.
# By default we use an unused uid of 1234.
# This is placed here to avoid redownloading package on uid change
ARG oioioi_uid=1234

# Bash as shell, setup folders, create oioioi user
RUN rm /bin/sh && ln -s /bin/bash /bin/sh && \
    mkdir -pv /sio2/oioioi && \
    mkdir -pv /sio2/sandboxes && \
    useradd -U oioioi -m -d /home/oioioi/ -u $oioioi_uid && \
    echo "oioioi ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers && \
    chown -R oioioi:oioioi /sio2

# Modify locale
RUN sed -i -e "s/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/" /etc/locale.gen && \
    locale-gen

# Installing python dependencies
USER oioioi

ENV UV_NO_CACHE=1
ENV BERKELEYDB_DIR=/usr

WORKDIR /sio2/oioioi

COPY --chown=oioioi:oioioi . ./
ENV UV_PROJECT_ENVIRONMENT=/sio2/.venv
RUN uv sync --all-groups

# needed for oioioi-create-config
ENV VIRTUAL_ENV=/sio2/.venv
# add the venv created by uv to PATH
ENV PATH=$VIRTUAL_ENV/bin:$PATH

# Installing node dependencies
ENV PATH=$PATH:/sio2/oioioi/node_modules/.bin

RUN pnpm install --frozen-lockfile
RUN pnpm run build

RUN uv run oioioi-create-config /sio2/deployment

WORKDIR /sio2/deployment

RUN mkdir -p /sio2/deployment/logs/{supervisor,runserver}

# The stage below is independent of base and can be built in parallel to optimize build time.
FROM python:3.13-slim AS development-sandboxes

ENV DOWNLOAD_DIR=/sio2/sandboxes
ENV MANIFEST_URL=https://downloads.sio2project.mimuw.edu.pl/sandboxes/Manifest

# Download the file and invalidate the cache if the Manifest checksum changes.
ADD $MANIFEST_URL /sio2/Manifest

RUN apt-get update && \
    apt-get install --no-install-recommends -y curl wget bash && \
    apt-get clean

COPY download_sandboxes.sh /download_sandboxes.sh
RUN chmod +x /download_sandboxes.sh

# Run script to download sandbox data from the given Manifest.
RUN ./download_sandboxes.sh -q -y -d $DOWNLOAD_DIR -m $MANIFEST_URL

# For production (or dev with filetracker): Upload sandboxes to built-in filetracker during build
# For dev: The sandboxes will be re-uploaded to s3dedup at runtime via oioioi_init.sh
FROM base AS base_with_sandboxes
COPY --from=development-sandboxes /sio2/sandboxes /sio2/sandboxes

FROM base_with_sandboxes AS base_with_populated_filetracker
RUN ./manage.py supervisor > /dev/null --daemonize \
    --nolaunch={uwsgi,unpackmgr,evalmgr,rankingsd,mailnotifyd,sioworkersd,receive_from_workers} && \
    /sio2/oioioi/wait-for-it.sh -t 60 "127.0.0.1:9999" && \
    ./manage.py upload_sandboxes_to_filetracker -d /sio2/sandboxes && \
    ./manage.py supervisor stop all

FROM base_with_sandboxes AS development

FROM base AS development_filetracker
COPY --from=base_with_populated_filetracker /sio2/deployment/media /sio2/deployment/media
