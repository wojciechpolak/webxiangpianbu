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
- Map feature (Leaflet, Mapbox, Google Maps)
- Language localization

Installation
------------

    $ git clone https://github.com/wojciechpolak/webxiangpianbu.git
    $ cd webxiangpianbu
    $ virtualenv .
    $ source bin/activate
    $ pip install -r requirements.txt

or without virtualenv:

    $ git clone...
    $ cd webxiangpianbu
    $ sudo pip install -r requirements.txt

Before you install `Pillow` via PIP (from requirements.txt), make sure
you already have installed `libjpeg-devel` (or similar package).
You will also need the `python-devel` package.

Next steps:

1. Copy `webxiang/settings-sample.py` to `webxiang/settings.py`
   and modify it to your needs.
2. Make sure that `cached` directory (settings.CACHE_DIR) exists
   and has write permissions by your web server.
3. Optionally, run `python manage.py compilemessages` (if you have
   `gettext` installed).
4. python manage.py collectstatic

Web Application Deployment
--------------------------

See https://docs.djangoproject.com/en/dev/howto/deployment/
for usual Django applications deployment.

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

* http://wojciechpolak.org/photos/
