FROM python:3.10-slim@sha256:364bb889cb48b1e0d66b8aa73b1e952f1d072864205f8abc667f0a15d84de040

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install .
RUN rm -rf /config-merger/*
