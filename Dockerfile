FROM python:3.12-slim@sha256:10f3aaab98db50cba827d3b33a91f39dc9ec2d02ca9b85cbc5008220d07b17f3

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install .
RUN rm -rf /config-merger/*
