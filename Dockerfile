FROM python:3.11-slim@sha256:dcca7339f0426d2fdb33e8fbbe05cca4b39af30430602c8c894822cf81d618ab

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install .
RUN rm -rf /config-merger/*
