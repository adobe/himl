FROM python:3.10.4-slim@sha256:425d893546dbb7c9984aad25cd219a4f9086e48e6990c0368aa2ce3670e9bc6e

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install -r requirements.txt
RUN pip3 install .
RUN rm -rf /config-merger/*
