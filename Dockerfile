FROM python:3.10.4-slim@sha256:9dc81e50d552404344b5c343815ceef332da89df67cafbf31b5560a7ded3df12

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install -r requirements.txt
RUN pip3 install .
RUN rm -rf /config-merger/*
