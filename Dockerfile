FROM python:3.12-slim@sha256:e38062874c7a45323cdd9a4c5241d18821c320a6c761f20a4640523ebf42b03e

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install .
RUN rm -rf /config-merger/*
