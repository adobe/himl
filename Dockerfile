FROM python:3.14-slim

WORKDIR /config-merger

# Copy only the necessary files for installation
COPY pyproject.toml ./
COPY himl/ ./himl/
COPY README.md ./
COPY LICENSE ./
COPY .git/ ./.git/

RUN apt-get update && apt-get install -y make curl git && rm -rf /var/lib/apt/lists/*

# Install the package with all optional dependencies for full functionality
RUN python -m pip install --upgrade pip && pip3 install .[all]

# Clean up source files after installation (keep only installed package)
RUN find /config-merger -mindepth 1 -delete
