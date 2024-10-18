FROM python:3.13-slim@sha256:02699283cc784486281bb4bdf233b8cf443f038d9b9c91873d31bd4cbd622a3d

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install .
RUN rm -rf /config-merger/*
