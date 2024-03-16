ARG python=python:3.11-slim-bookworm

FROM ${python} AS webxiang-builder-python
RUN apt update -y
RUN apt install -y gcc g++
RUN apt-get clean
WORKDIR /app
RUN python -m venv /venv
ENV PATH=/venv/bin:$PATH
RUN pip install --no-cache-dir poetry==1.7.1
COPY pyproject.toml .
COPY poetry.lock .
RUN poetry config virtualenvs.create false
RUN poetry config installer.max-workers 10
RUN poetry install --no-dev -n

FROM ${python}
RUN apt update -y
RUN apt install -y curl gettext procps
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
RUN usermod -a -G users www-data
RUN chgrp -R users /app/webxiang/static && chmod -R g+w /app/webxiang/static
RUN python manage.py compilemessages
ENV PYTHONPATH "${PYTHONPATH}:/app"
EXPOSE 80
COPY conf/docker/etc/supervisord.conf /etc/supervisord.conf

HEALTHCHECK --interval=60m --timeout=3s CMD curl -f http://localhost/ || exit 1
CMD /app/entrypoint.sh
