FROM python:3.10.4-slim@sha256:80ebadfc9b83cf037ebe9a7db0631101b7c18c58f4197de0ef2badb268a35a45

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install -r requirements.txt
RUN pip3 install .
RUN rm -rf /config-merger/*
