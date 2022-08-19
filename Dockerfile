FROM python:3.10-slim@sha256:cf85cd32e60184a94d88a0103c289d09024abffaa77680d116d7cc837668ea15

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install .
RUN rm -rf /config-merger/*
