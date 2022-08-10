FROM python:3.10.5-slim@sha256:f9f03f46267e182193544299504687e711c623e2a085323138f94ed9b01ce641

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install .
RUN rm -rf /config-merger/*
