FROM python:3.10.3-slim@sha256:de3f55fdc4402a88db7cb53b82a053e247b00dac98c67fb2001a5998044a528a

WORKDIR /config-merger

ADD . /config-merger/

RUN apt-get update && apt-get install -y make curl

RUN python -m pip install --upgrade pip && pip3 install -r requirements.txt
RUN pip3 install .
RUN rm -rf /config-merger/*
