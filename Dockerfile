FROM python:3.11-slim@sha256:cd6e574ff6ad2ac75184ad90e4e374842cfc36ae21bc2f773531ac65f6939991

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install .
RUN rm -rf /config-merger/*
