WebXiangpianbu
==============

WebXiangpianbu is a photo album organizer written in Python/Django.
It can work as a dynamic web application photo gallery or as a static
site generator.

Features
--------

- Free, self-hosted web application
- No database required
- Highly customizable (albums, templates, styles)
- Mobile friendly
- EXIF and Geotagging extracting
- Map feature (Leaflet, Mapbox)
- Language localization

Installation
------------

Install all necessary dependencies using [uv](https://docs.astral.sh/uv/).

```shell
$ uv sync
```

Next steps:

1. Copy `webxiang/settings_sample.py` to `webxiang/settings.py`
   and modify it to your needs.
2. Optionally, run `uv run manage.py compilemessages` (if you have
   `gettext` installed).
3. uv run manage.py collectstatic

Testing
-------

Install development dependencies and the Playwright browser runtime:

```shell
uv sync --group dev
uv run python -m playwright install chromium
```

Run the test and code quality checks:

```shell
uv run pytest
uv run ruff check
uv run ty check
uv run mypy .
```

If you want only the fast unit tests, exclude the browser marker:

```shell
uv run pytest -m "not e2e"
```

Visual regression tests
-----------------------

Visual regression testing is layered on top of those same browser tests.
Run the baseline refresh command once when you intentionally accept a new
UI state, then rerun the comparison command to check for visual drift:

```shell
./scripts/vrt-docker.sh baseline
```

```shell
./scripts/vrt-docker.sh compare
```

Web Application Deployment
--------------------------

See https://docs.djangoproject.com/en/dev/howto/deployment/
for usual Django applications deployment.

Docker Deployment
-----------------

```shell
./scripts/build-docker.sh
# [adjust files in the `run` folder]
docker-compose up
```

Tools
-----

`generate.py` -- generate albums from photo files.

```shell
uv run tools/generate.py --album-dir=albums/ ~/photos/vacation/ ~/webxiang/static/data/vacation
uv run tools/generate.py --help
# next, adjust the generated vacation.yaml
```

`convert.py` -- convert albums between different file formats (YAML, JSON).

```shell
uv run tools/convert.py 'albums/*.yaml' tmp/
```

Static Site Generator
---------------------

```shell
uv run tools/generate.py ~/photos/vacation/ ~/tmp/vacation
uv run tools/staticgen.py --quick=~/tmp/vacation --copy
uv run tools/staticgen.py --help
```

Sample Galleries
----------------

* https://wojciechpolak.org/photos/
