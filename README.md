WebXiangpianbu
==============

WebXiangpianbu is a photo album organizer written in Python/Django.

Features
--------

- Free, self-hosted web application
- No database required
- Highly customizable (albums, templates, styles)
- Mobile friendly
- Localization

Deployment
----------

See https://docs.djangoproject.com/en/dev/howto/deployment/
for usual Django applications deployment.

1. Change working directory to `webxiang'.
2. Copy webxiang/settings-sample.py to webxiang/settings.py
   and modify it to your needs.
3. Make sure that `cache' directory (settings.CACHE_DIR) exists
   and has write permissions by your web server.
4. Optionally, run `python manage.py compilemessages' (if you have
   `gettext' installed).
5. python manage.py collectstatic

Tools
-----

* generate.py -- generates albums from photo files.

    $ tools/generate.py --album-dir=albums/ ~/photos/vacation/ \
    ~/webxiang/static/data/vacation

* convert.py -- converts albums between different formats (YAML, JSON).

    $ tools/convert.py 'albums/*.yaml' tmp/

Sample Galleries
----------------

* http://wojciechpolak.org/photos/
