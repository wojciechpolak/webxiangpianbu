"""
# Django settings for WebXiangpianbu project.

Configure an installation through environment variables or a `.env` file in
the project root (see `.env.example`). For anything beyond that, create
`webxiang/settings_local.py`: it is executed at the end of this module, so it
can override or modify any setting below. Both are ignored by Git.
"""

import os
from pathlib import Path
from typing import Any

from webxiang.env import get_bool, get_env, get_list, load_dotenv

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
BASE_DIR = SITE_ROOT
PROJECT_ROOT = os.path.dirname(SITE_ROOT)

if get_bool(os.environ, 'WEBXIANG_LOAD_DOTENV', default=True):
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
ENV = os.environ


def _project_path(value: str) -> str:
    return os.path.abspath(os.path.join(PROJECT_ROOT, value))


# Holds albums, photos and optional template/static overrides.
RUN_DIR = _project_path(get_env(ENV, 'RUN_DIR', default='run'))

DEBUG = get_bool(ENV, 'DEBUG', 'APP_DEBUG', default=True)

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = get_list(ENV, 'ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# Local time zone for this installation. Choices can be found here:
# https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
TIME_ZONE = get_env(ENV, 'TIME_ZONE', default='UTC')

LANGUAGES = (
    ('en', 'English'),
    ('pl', 'Polski'),
)
LANGUAGE_CODE = get_env(ENV, 'LANGUAGE_CODE', default='en-us')
LANGUAGE_COOKIE_NAME = 'lang'
DEFAULT_LANGUAGE = 1

# Directories where Django looks for translation files.
LOCALE_PATHS = (os.path.join(PROJECT_ROOT, 'locale'),)

CACHES = {
    'default': {
        # e.g. django.core.cache.backends.memcached.PyMemcacheCache
        'BACKEND': get_env(
            ENV, 'CACHE_BACKEND', default='django.core.cache.backends.dummy.DummyCache'
        ),
        'LOCATION': get_env(ENV, 'CACHE_LOCATION', default='127.0.0.1:11211'),
        'KEY_PREFIX': 'webxiang',
    },
}

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = get_env(ENV, 'STATIC_URL', default='/static/')

STORAGES = {
    'staticfiles': {
        'BACKEND': 'pipeline.storage.PipelineManifestStorage',
    }
}
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)
STATICFILES_DIRS = (
    os.path.join(RUN_DIR, 'static'),
    os.path.join(SITE_ROOT, 'static'),
)

PIPELINE: dict[str, Any] = {
    'DISABLE_WRAPPER': True,
    'JS_COMPRESSOR': None,
    'CSS_COMPRESSOR': None,
    # One source per package: an output that bundled several files under
    # one of their own names would be read back as a source on the next
    # collectstatic run, piling up copies.
    'JAVASCRIPT': {
        'jquery': {
            'source_filenames': ('js/jquery.min.js',),
            'output_filename': 'js/jquery.min.js',
        },
        'gallery': {
            'source_filenames': ('js/gallery.js',),
            'output_filename': 'js/gallery.js',
        },
    },
    'STYLESHEETS': {
        'base.css': {
            'source_filenames': ('css/base.css',),
            'output_filename': 'css/base.css',
        },
        'light.css': {
            'source_filenames': ('css/light.css',),
            'output_filename': 'css/light.css',
        },
        'photo.css': {
            'source_filenames': ('css/photo.css',),
            'output_filename': 'css/photo.css',
        },
    },
}

# Make this unique, long, and don't share it with anybody. Outside DEBUG
# there is no fallback: Django refuses to use an empty key.
SECRET_KEY = get_env(
    ENV,
    'WEBXIANG_SECRET_KEY',
    'SECRET_KEY',
    default='dev-insecure-secret-key' if DEBUG else '',
)

MIDDLEWARE = [
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
]

ROOT_URLCONF = 'webxiang.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # Put user-menu.html and user-footer.html overrides here.
            os.path.join(RUN_DIR, 'templates'),
            os.path.join(SITE_ROOT, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'webxiang.wsgi.application'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'pipeline',
    'webxiang',
)

SITE_ID = 1

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See https://docs.djangoproject.com/en/dev/topics/logging/ for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'filters': {'require_debug_false': {'()': 'django.utils.log.RequireDebugFalse'}},
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'main': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}

#
# WebXiangpianbu specific settings.
#

SITE_URL = get_env(ENV, 'SITE_URL', default='https://www.example.org/')

WEBXIANG_PHOTOS_URL = get_env(ENV, 'WEBXIANG_PHOTOS_URL', default='/data/')

# Absolute path to the directory containing photo files (JPEGs).
WEBXIANG_PHOTOS_ROOT = _project_path(
    get_env(ENV, 'WEBXIANG_PHOTOS_ROOT', default=os.path.join(RUN_DIR, 'data'))
)

ALBUM_DIR = _project_path(
    get_env(ENV, 'ALBUM_DIR', default=os.path.join(RUN_DIR, 'albums'))
)

COPYRIGHT_OWNER = get_env(ENV, 'COPYRIGHT_OWNER', default='Your Name')

WXPB_SETTINGS = {
    # leaflet, mapbox
    'geo_map_plugin': get_env(ENV, 'GEO_MAP_PLUGIN', default='leaflet'),
    'geo_leaflet_layers': {
        'OpenStreetMap': {'id': 'osm.mapnik', 'is_default': True},
        # 'Custom': {'id': 'MAPID', 'type': 'mapbox'}
    },
}
if mapbox_access_token := get_env(ENV, 'MAPBOX_ACCESS_TOKEN'):
    WXPB_SETTINGS['mapbox_accessToken'] = mapbox_access_token

SETTINGS_LOCAL_PATH = Path(SITE_ROOT) / 'settings_local.py'
if (
    get_bool(ENV, 'WEBXIANG_SETTINGS_LOCAL', default=True)
    and SETTINGS_LOCAL_PATH.is_file()
):
    exec(  # noqa: S102 - settings_local.py is a trusted local override
        compile(SETTINGS_LOCAL_PATH.read_text(), str(SETTINGS_LOCAL_PATH), 'exec'),
        globals(),
    )
