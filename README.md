WebXiangpianbu
==============

WebXiangpianbu is a photo album organizer written in Python/Django.
It can work as a dynamic web application photo gallery or as a static
photo gallery (website) generator.

Features
--------

- Free, self-hosted web application
- No database required
- Highly customizable (albums, templates, styles)
- Mobile friendly
- Localization

Installation
------------

	$ git clone https://github.com/wojciechpolak/webxiangpianbu.git
	$ cd webxiangpianbu
	$ virtualenv .
	$ source bin/activate
	$ pip install -r requirements.txt

Before you install `Pillow` via PIP (from requirements.txt), make sure
you already have installed `libjpeg-devel` (or similar package).

Web Application Deployment
--------------------------

1. Copy `webxiang/settings-sample.py` to `webxiang/settings.py`
   and modify it to your needs.
2. Make sure that `cache` directory (settings.CACHE_DIR) exists
   and has write permissions by your web server.
3. Optionally, run `python manage.py compilemessages` (if you have
   'gettext' installed).
4. python manage.py collectstatic

See https://docs.djangoproject.com/en/dev/howto/deployment/
for usual Django applications deployment.

Tools
-----

generate.py -- generates albums from photo files.

    $ tools/generate.py --album-dir=albums/ ~/photos/vacation/ ~/webxiang/static/data/vacation
    $ tools/generate.py --help

convert.py -- converts albums between different file formats (YAML, JSON).

    $ tools/convert.py 'albums/*.yaml' tmp/

Static Website Generation
-------------------------

    $ tools/generate.py ~/photos/vacation/ ~/tmp/vacation
    $ tools/staticgen.py --quick=~/tmp/vacation --copy
    $ tools/staticgen.py --help

Sample Galleries
----------------

* http://wojciechpolak.org/photos/
