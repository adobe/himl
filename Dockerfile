FROM python:3.10.5-slim@sha256:ca78039cbd3772addb9179953bbf8fe71b50d4824b192e901d312720f5902b22

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install .[extras]
RUN rm -rf /config-merger/*
