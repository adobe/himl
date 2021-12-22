FROM python:3.10.1-slim@sha256:dd3016f846b8f88d8f6c28b43f1da899f07259121aff403091e6f89a703c3d36

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install -r requirements.txt
RUN pip3 install .
RUN rm -rf /config-merger/*
