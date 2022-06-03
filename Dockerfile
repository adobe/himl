FROM python:3.10.4-slim@sha256:557745c5e06c874ba811efe2e002aff21b6cc405b828952fcfa16dea52d56dbb

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install -r requirements.txt
RUN pip3 install .
RUN rm -rf /config-merger/*
