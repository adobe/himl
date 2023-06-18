FROM python:3.11-slim@sha256:55221704bcc5432f978bc5184d58f54c93ad25313363a1d0db20606a4cf2aef7

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install .
RUN rm -rf /config-merger/*
