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

1. Optionally, copy `.env.example` to `.env` and adjust it. The
   committed `webxiang/settings.py` reads its configuration from
   environment variables and from `.env`; the defaults work for local
   development. Outside `DEBUG` mode, set `WEBXIANG_SECRET_KEY`.
   For anything the variables don't cover (custom map layers, extra
   apps, and so on), create `webxiang/settings_local.py`. It runs at the
   end of `webxiang/settings.py`, so it can override or modify any
   setting. Both files are ignored by Git.
2. Optionally, run `uv run manage.py compilemessages` (if you have
   `gettext` installed).
3. uv run manage.py collectstatic

Albums go in `run/albums` and photos in `run/data` (see `RUN_DIR`).
Templates in `run/templates` (e.g. `user-menu.html`, `user-footer.html`)
override the built-in ones.

Upgrading from an older version: `webxiang/settings.py` used to be a
local, untracked copy of `settings_sample.py`. Move your changes into
`.env` or `webxiang/settings_local.py`, then delete that file before
running `git pull`.

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
# [set WEBXIANG_SECRET_KEY in `.env`, adjust files in the `run` folder]
docker-compose up
```

Docker uses `run/settings_docker.py`, a thin overlay on `webxiang.settings`.

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
