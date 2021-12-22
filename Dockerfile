FROM python:3.10.1-slim@sha256:a58c7e5266d140d274ce60160ff8b680c820602d729ef28b631ca0fba1d03d34

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install -r requirements.txt
RUN pip3 install .
RUN rm -rf /config-merger/*
