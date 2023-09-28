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

Install all needed dependencies using [Poetry](https://python-poetry.org/) or PIP.

```shell
$ poetry install
or
$ pip install -r requirements.txt
```

Next steps:

1. Copy `webxiang/settings_sample.py` to `webxiang/settings.py`
   and modify it to your needs.
2. Optionally, run `python manage.py compilemessages` (if you have
   `gettext` installed).
3. python manage.py collectstatic

Web Application Deployment
--------------------------

See https://docs.djangoproject.com/en/dev/howto/deployment/
for usual Django applications deployment.

Docker Deployment
-----------------

```shell
./scripts/build-docker.sh
[adjust files in the `run` folder]
docker-compose up
```

Tools
-----

generate.py -- generate albums from photo files.

    $ tools/generate.py --album-dir=albums/ ~/photos/vacation/ ~/webxiang/static/data/vacation
    $ tools/generate.py --help
    next, adjust the generated vacation.yaml

convert.py -- convert albums between different file formats (YAML, JSON).

    $ tools/convert.py 'albums/*.yaml' tmp/

Static Site Generator
---------------------

    $ tools/generate.py ~/photos/vacation/ ~/tmp/vacation
    $ tools/staticgen.py --quick=~/tmp/vacation --copy
    $ tools/staticgen.py --help

Sample Galleries
----------------

* https://wojciechpolak.org/photos/
