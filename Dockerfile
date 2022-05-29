FROM python:3.10.4-slim@sha256:700f5a4d88091b9963473b949567f1518ff5589c4035350cd03a1762cadb2190

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install -r requirements.txt
RUN pip3 install .
RUN rm -rf /config-merger/*
