FROM python:3.14-slim

WORKDIR /config-merger

# Copy only the necessary files for installation
COPY pyproject.toml ./
COPY himl/ ./himl/
COPY README.md ./
COPY LICENSE ./
RUN apt-get update && apt-get install -y make curl && rm -rf /var/lib/apt/lists/*

ARG SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION}

# Install the package with all optional dependencies for full functionality
RUN python -m pip install --upgrade pip && pip3 install .[all]

# Clean up source files after installation (keep only installed package)
RUN find /config-merger -mindepth 1 -delete
