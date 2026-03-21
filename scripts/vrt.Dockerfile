FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m pip install --no-cache-dir uv
