FROM python:3.10.4-slim@sha256:a0e8f2985ecb43fdb5dc9ccb6d483ab2f73290545e9dd5e34dc6fa4ce7c8a190

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install -r requirements.txt
RUN pip3 install .
RUN rm -rf /config-merger/*
