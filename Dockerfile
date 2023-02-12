ARG python=python:3.11-slim

FROM ${python} AS webxiang-builder-python
RUN apt update -y
RUN apt install -y gcc
RUN apt-get clean
WORKDIR /app
RUN python -m venv /venv
ENV PATH=/venv/bin:$PATH
RUN pip install --no-cache-dir poetry
COPY pyproject.toml .
COPY poetry.lock .
RUN poetry config virtualenvs.create false
RUN poetry install -n

FROM ${python}
RUN apt update -y
RUN apt install -y curl gettext nginx procps
RUN pip install --no-cache-dir supervisor
RUN apt-get clean
RUN echo 'alias ll="ls -l"' >>~/.bashrc
RUN mkdir /app /app/run
COPY --from=webxiang-builder-python /venv /venv
ENV PATH=/venv/bin:$PATH
ENV DJANGO_SETTINGS_MODULE=run.settings_docker
WORKDIR /app
COPY conf/docker/entrypoint.sh .
ADD run run
ADD locale locale
ADD webxiang webxiang
COPY manage.py .
RUN python manage.py compilemessages
RUN python manage.py collectstatic --no-input
ENV PYTHONPATH "${PYTHONPATH}:/app"
EXPOSE 80
COPY conf/docker/etc/supervisord.conf /etc/supervisord.conf
COPY conf/docker/etc/nginx/ /etc/nginx/

HEALTHCHECK --interval=60m --timeout=3s CMD curl -f http://localhost/ || exit 1
CMD /app/entrypoint.sh
