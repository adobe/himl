FROM python:3.10.6-slim@sha256:59129c9fdea259c6a9b6d9c615c065c336aca680ee030fc3852211695a21c1cf

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install .
RUN rm -rf /config-merger/*
