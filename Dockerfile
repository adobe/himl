FROM python:3.10.1-slim@sha256:73561a44fb5c181399a3dc21513e2188a62f052826bd4e15b0ddc5fe4a676c31

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install -r requirements.txt
RUN pip3 install .
RUN rm -rf /config-merger/*
