FROM python:3.10-slim@sha256:6862d8ed663a47f649ba5aababed01e44741a032e80d5800db619f5113f65434

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install .
RUN rm -rf /config-merger/*
