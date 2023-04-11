FROM python:3.7

ENV PYTHONUNBUFFERED 1

RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y \
        nginx \
        proot \
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
        sox \
        flite \
        nodejs \
        npm \
        locales && \
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

RUN pip3 install --user psycopg2-binary==2.8.6 twisted uwsgi && \
    pip3 cache purge

WORKDIR /sio2/oioioi

COPY --chown=oioioi:oioioi setup.py requirements.txt ./
RUN pip3 install -r requirements.txt --user && \
    pip3 cache purge
COPY --chown=oioioi:oioioi requirements_static.txt ./
RUN pip3 install -r requirements_static.txt --user && \
    pip3 cache purge
COPY --chown=oioioi:oioioi requirements_talent.txt ./
RUN pip3 install -r requirements_talent.txt --user && \
    pip3 cache purge

COPY --chown=oioioi:oioioi . /sio2/oioioi

RUN oioioi-create-config /sio2/deployment

WORKDIR /sio2/deployment

RUN sed -i -e \
       "s/SERVER = 'django'/SERVER = 'uwsgi-http'/g;\
        s/DEBUG = True/DEBUG = False/g;\
        s/django.db.backends./django.db.backends.postgresql/g;\
        s/#BROKER_URL/BROKER_URL/g;\
        s/#FILETRACKER_LISTEN_ADDR/FILETRACKER_LISTEN_ADDR/g;\
        s/#FILETRACKER_LISTEN_PORT/FILETRACKER_LISTEN_PORT/g;\
        s|#FILETRACKER_URL = '.*'|FILETRACKER_URL = 'http://web:9999'|g;\
        s/#*RUN_SIOWORKERSD$/RUN_SIOWORKERSD/g;\
        s/#SIOWORKERS_LISTEN_ADDR/SIOWORKERS_LISTEN_ADDR/g;\
        s/#SIOWORKERS_LISTEN_PORT/SIOWORKERS_LISTEN_PORT/g;\
        s/RUN_LOCAL_WORKERS = True/RUN_LOCAL_WORKERS = False/g;\
        s/USE_UNSAFE_EXEC = True/USE_UNSAFE_EXEC = False/g;\
        \$afrom basic_settings import *\n" \
        settings.py && \
    cp /sio2/oioioi/oioioi/selenium_settings.py selenium_settings.py && \
    mkdir -p /sio2/deployment/{sockets,logs/{supervisor,runserver}} && \
    sudo ln -fs /sio2/deployment/nginx-site.conf /etc/nginx/sites-available/default

# Download sandboxes
RUN ./manage.py supervisor > /dev/null --daemonize --nolaunch=uwsgi \
        --nolaunch=rankingsd --nolaunch=mailnotifyd --nolaunch=evalmgr \
        --nolaunch=unpackmgr --nolaunch=sioworkersd \
        --nolaunch=receive_from_workers --nolaunch=notifications-server && \
    ./manage.py download_sandboxes -q -y -c /sio2/sandboxes compiler-fpc.2_6_2 \
        compiler-gcc.10_2_1 exec-sandbox vcpu_exec-sandbox proot-sandbox \
        proot-sandbox_amd64 null-sandbox sio2jail_exec-sandbox-1.4.2 && \
    ./manage.py supervisor stop all && \
    rm -rf /sio2/deployment/cache
