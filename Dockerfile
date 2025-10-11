FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED 1

#RUN dpkg --add-architecture i386
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
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
        python3-pip \
        nodejs \
        npm && \
    apt-get clean && \
    rm -rf /usr/share/doc/texlive*

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
RUN pip3 install uv

USER oioioi

RUN uv venv /home/oioioi/.local

ENV UV_NO_CACHE 1
ENV VIRTUAL_ENV /home/oioioi/.local
ENV PATH $PATH:/home/oioioi/.local/bin/

ENV BERKELEYDB_DIR /usr
RUN uv pip install psycopg2-binary twisted uwsgi
RUN uv pip install bsddb3==6.2.7

WORKDIR /sio2/oioioi

COPY --chown=oioioi:oioioi . ./
RUN uv pip install -r requirements.txt filetracker[server]
RUN uv pip install -r requirements_static.txt

# Installing node dependencies
ENV PATH $PATH:/sio2/oioioi/node_modules/.bin

RUN npm ci
RUN npm run build

RUN oioioi-create-config /sio2/deployment

WORKDIR /sio2/deployment

RUN mkdir -p /sio2/deployment/logs/{supervisor,runserver}

# The stage below is independent of base and can be built in parallel to optimize build time.
FROM python:3.11-slim AS development-sandboxes

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

# This additional stage allows for not including the downloaded sandboxes twice
# in the final image. When BuildKit will be more widespread as the default
# in docker installations, this can be replaced with `RUN --mount`.
FROM base AS populated_filetracker

COPY --from=development-sandboxes /sio2/sandboxes /sio2/sandboxes
RUN chmod +x /sio2/oioioi/download_sandboxes.sh

RUN ./manage.py supervisor > /dev/null --daemonize \
    --nolaunch={uwsgi,unpackmgr,evalmgr,rankingsd,mailnotifyd,sioworkersd,receive_from_workers} && \
    /sio2/oioioi/wait-for-it.sh -t 60 "127.0.0.1:9999" && \
    ./manage.py upload_sandboxes_to_filetracker -d /sio2/sandboxes && \
    ./manage.py supervisor stop all

FROM base AS development
COPY --from=populated_filetracker /sio2/deployment/media /sio2/deployment/media
