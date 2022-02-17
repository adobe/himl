FROM python:3.10.2-slim@sha256:42d13fdfccf5d97bd23f9c054f22bde0451a3da0a7bb518bcd95fec6be89b50d

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install -r requirements.txt
RUN pip3 install .
RUN rm -rf /config-merger/*
