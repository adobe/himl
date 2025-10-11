FROM python:3.14-slim@sha256:5cfac249393fa6c7ebacaf0027a1e127026745e603908b226baa784c52b9d99b

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install -r requirements.txt && pip3 install .
RUN rm -rf /config-merger/*
