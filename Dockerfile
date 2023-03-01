FROM python:3.10-slim@sha256:fcf375288c9348c9708cc7ea3d511b512224219fdc164b6960b3ce85288e1cbf

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install .
RUN rm -rf /config-merger/*
