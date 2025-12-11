ARG python=python:3.14-slim-trixie
ARG TARGETARCH

FROM ${python} AS webxiang-builder-python
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ARG TARGETARCH
ENV TARGETARCH=${TARGETARCH:-amd64}

RUN apt update -y
RUN apt install -y gcc g++
RUN apt-get clean

WORKDIR /app
ENV UV_NO_DEV=1

RUN --mount=type=cache,target=/root/.cache/uv,id=uv-${TARGETARCH} \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable

COPY pyproject.toml .
COPY uv.lock .
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-${TARGETARCH} \
    uv sync --locked --no-editable

FROM ${python}
RUN apt update -y
RUN apt install -y curl gettext procps libexpat1
RUN pip install --no-cache-dir supervisor
RUN apt-get clean
RUN echo 'alias ll="ls -l"' >>~/.bashrc
RUN mkdir /app /app/run
COPY --from=webxiang-builder-python --chown=app:app /app/.venv /app/.venv

ENV PATH=/app/.venv/bin:$PATH
ENV DJANGO_SETTINGS_MODULE=run.settings_docker
WORKDIR /app
COPY conf/docker/entrypoint.sh .
ADD run run
ADD locale locale
ADD webxiang webxiang
COPY manage.py .
RUN usermod -a -G users www-data
RUN chgrp -R users /app/webxiang/static && chmod -R g+w /app/webxiang/static
RUN python manage.py compilemessages
EXPOSE 80
COPY conf/docker/etc/supervisord.conf /etc/supervisord.conf

HEALTHCHECK --interval=60m --timeout=3s CMD curl -f http://localhost/ || exit 1
CMD ["/app/entrypoint.sh"]
