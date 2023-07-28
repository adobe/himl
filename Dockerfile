FROM python:3.11-slim@sha256:2e064d6f7c227a6574cff77261a089c068fc19ab4b99309c27e0d5c9829de686

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install .
RUN rm -rf /config-merger/*
