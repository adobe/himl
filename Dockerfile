FROM python:3.11-slim@sha256:7ad180fdf785219c4a23124e53745fbd683bd6e23d0885e3554aff59eddbc377

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install .
RUN rm -rf /config-merger/*
