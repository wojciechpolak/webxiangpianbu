# Django settings for WebXiangpianbu project.

import os
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
BASE_DIR = SITE_ROOT

DEBUG = False

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
]

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'UTC'

LANGUAGES = (
    ('en', u'English'),
    ('pl', u'Polski'),
)
LANGUAGE_CODE = 'en-us'
LANGUAGE_COOKIE_NAME = 'lang'
DEFAULT_LANGUAGE = 1

# Directories where Django looks for translation files.
LOCALE_PATHS = (
    os.path.join(SITE_ROOT, '../locale'),
)

CACHES = {
    'default': {
#       'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'LOCATION': '127.0.0.1:11211',
        'KEY_PREFIX': 'webxiang',
    },
}

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = False

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = os.path.abspath(os.path.join(SITE_ROOT, '../static'))

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

STATICFILES_STORAGE = 'pipeline.storage.PipelineManifestStorage'
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)
STATICFILES_DIRS = (
    os.path.join(SITE_ROOT, 'static'),
)

PIPELINE = {
    'DISABLE_WRAPPER': True,
    'JS_COMPRESSOR': None,
    'CSS_COMPRESSOR': None,
    'JAVASCRIPT': {
        'gallery': {
            'source_filenames': (
                'js/jquery.min.js',
                'js/gallery.js',
            ),
            'output_filename': 'js/gallery.js',
        },
    }
}

# Make this unique, long, and don't share it with anybody.
SECRET_KEY = ''

assert SECRET_KEY != '', 'SECRET_KEY must be long and unique.'

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
# See http://docs.djangoproject.com/en/dev/topics/logging for
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
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
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
    }
}

#
# WebXiangpianbu specific settings.
#

SITE_URL = 'www.example.org/'

WEBXIANG_PHOTOS_URL = '/data/'

# Absolute path to the directory containing photo files (JPEGs).
WEBXIANG_PHOTOS_ROOT = '/home/user/photos/data/'

ALBUM_DIR = os.path.join(SITE_ROOT, '../albums')

COPYRIGHT_OWNER = 'Your Name'

WXPB_SETTINGS = {
    'geo_map_plugin': 'leaflet',  # leaflet, mapbox
    'geo_leaflet_layers': {
        'OpenStreetMap': {'id': 'osm.mapnik', 'is_default': True},
        # 'Custom': {'id': 'MAPID', 'type': 'mapbox'}
    },
    #'mapbox_accessToken': '',
}
