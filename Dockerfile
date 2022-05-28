FROM python:3.10.4-slim@sha256:27579438c29f7529fbeccc67535152740c5ef02e1094a68bc9bf997e3136ba4c

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install -r requirements.txt
RUN pip3 install .
RUN rm -rf /config-merger/*
