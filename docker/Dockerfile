# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

FROM debian:13
# If upgrading the version number from 13 to the next debian release, make sure to do the same
# also in the shell scripts stored in this directory.

WORKDIR /root

## Group A. Install dependencies from apt

# Part 0: basic utilities
RUN apt update -y -q && \
    apt install -y -qq ca-certificates curl git net-tools python3-pip sudo unzip vim wget

# Customize shell prompt color to better highlight that the user is running commands in the docker container
RUN echo 'PS1='"'"'\[\e]0;\u@\h: \w\a\]${debian_chroot:+($debian_chroot)}\[\033[01;38;5;27m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\$\[\033[00m\] '"'"'' >> /root/.bashrc && \
    echo "alias ls='ls --color=auto'"  >> /root/.bashrc && \
    echo "alias ll='ls -l'"  >> /root/.bashrc

# Allow system-wide install Python packages via pip
RUN rm /usr/lib/python3.13/EXTERNALLY-MANAGED

# Part 1: turing
RUN apt update -y -q && \
    apt install -y -qq chromium chromium-driver libpq-dev postgresql postgresql-client postgresql-contrib python3-psycopg2 python3-selenium

# postgres has created a new user, which should be allowed read-only access to /root
RUN chmod go+rx /root

# Part 2: mathrace-interaction
RUN apt update -y -q && \
    apt install -y -qq python3-jsondiff python3-paramiko python3-pycryptodome && \
    sed -i '1s/^/import warnings\nwarnings.filterwarnings("ignore", module="invoke.loader")\n/' /usr/lib/python3/dist-packages/invoke/loader.py

## Group B. Copy and installation of turing and mathrace-interaction

# Part 1: turing
COPY turing turing

RUN python3 -m pip install -r turing/requirements.txt && \
    sed -i '1s/^/import warnings\nwarnings.filterwarnings("ignore", module="django.http.request")\n/' /usr/local/lib/python3.13/dist-packages/django/http/request.py && \
    sed -i '1s/^/import warnings\nwarnings.filterwarnings("ignore", module="django.utils.encoding")\n/' /usr/local/lib/python3.13/dist-packages/django/utils/encoding.py

ENV DJANGO_SETTINGS_MODULE="Turing.settings" \
    PYTHONPATH=/root/turing

# Part 2: mathrace-interaction
COPY mathrace_interaction mathrace_interaction

RUN cd /root/mathrace_interaction && \
    python3 -m pip install .[tests] && \
    touch /usr/local/lib/python3.13/dist-packages/mockssh/py.typed

## Group C. Entrypoint setup.

# Set up entrypoint that:
# * creates and initialize databases on first run,
# * starts the server
COPY docker/entrypoint.sh /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
