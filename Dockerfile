FROM python:3.13-slim@sha256:087a9f3b880e8b2c7688debb9df2a5106e060225ebd18c264d5f1d7a73399db0

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install -r requirements.txt && pip3 install .
RUN rm -rf /config-merger/*
