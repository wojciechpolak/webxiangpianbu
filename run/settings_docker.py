#
# Django settings for WebXiangpianbu project (DOCKER VERSION).
#

import os
SITE_ROOT = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../webxiang/')
BASE_DIR = SITE_ROOT

DEBUG = False

ALLOWED_HOSTS = [
    os.getenv('VIRTUAL_HOST', ''),
    'localhost',
    'backend',
]

ADMINS = (
    ('Admin', 'example@example.org'),
)
MANAGERS = ADMINS

TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'en-us'
USE_I18N = True
USE_L10N = False

# Directories where Django looks for translation files.
LOCALE_PATHS = (
    os.path.join(SITE_ROOT, '../locale'),
)

# Caching, see http://docs.djangoproject.com/en/dev/topics/cache/#topics-cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': 'memcached:11211',
        'KEY_PREFIX': 'webxiang',
    },
}

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'YOUR-SECRET-KEY'

if SECRET_KEY == 'YOUR-SECRET-KEY':
    print('settings.SECRET_KEY must be long and unique!')

MIDDLEWARE = [
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(SITE_ROOT, '../run/templates'),
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

ROOT_URLCONF = 'webxiang.urls'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'pipeline',
    'webxiang',
)

SITE_ID = 1

STATIC_ROOT = os.path.abspath(os.path.join(SITE_ROOT, '../static'))
STATIC_URL = os.getenv('VIRTUAL_PATH', '/') + 'static/'

STATICFILES_STORAGE = 'pipeline.storage.PipelineManifestStorage'
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)
STATICFILES_DIRS = (
    os.path.join(SITE_ROOT, '../run/static'),
    os.path.join(SITE_ROOT, 'static'),
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        "handlers": ["console"],
        "level": "INFO",
    },
    'loggers': {
        'django.server': {
            'handlers': ['console'],
            'level': 'ERROR'
        },
        'main': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
    }
}

PIPELINE = {
    'DISABLE_WRAPPER': True,
    'JS_COMPRESSOR': None,
    'CSS_COMPRESSOR': None,
    'COMPILERS': ('pipeline.compilers.sass.SASSCompiler',),
    'SASS_BINARY': 'pysassc',
    'JAVASCRIPT': {
        'gallery': {
            'source_filenames': (
                'js/jquery.min.js',
                'js/gallery.js',
            ),
            'output_filename': 'js/gallery.js',
        },
    },
    'STYLESHEETS': {
        'base.css': {
            'source_filenames': (
                'css/base.css',
            ),
            'output_filename': 'css/base.css',
        },
        'light.css': {
            'source_filenames': (
                'css/light.css',
            ),
            'output_filename': 'css/light.css',
        },
        'photo.css': {
            'source_filenames': (
                'css/photo.css',
            ),
            'output_filename': 'css/photo.css',
        },
    },
}

#
# WebXiangpianbu specific settings.
#

SITE_URL = os.getenv('VIRTUAL_PATH', 'http://localhost:8080')
FORCE_SCRIPT_NAME = os.getenv('VIRTUAL_PATH', '/')

WEBXIANG_PHOTOS_URL = os.getenv('PHOTOS_BASE_URL', '/data/')

# Absolute path to the directory containing photo files (JPEGs).
WEBXIANG_PHOTOS_ROOT = '/app/run/data/'

ALBUM_DIR = '/app/run/albums'

COPYRIGHT_OWNER = 'Your Name'

WXPB_SETTINGS = {
    'geo_map_plugin': 'leaflet',  # leaflet, mapbox, google
    'geo_leaflet_layers': {
        'OpenStreetMap': {'id': 'osm.mapnik', 'is_default': True},
        # 'Custom': {'id': 'MAPID', 'type': 'mapbox'}
    },
    # 'mapbox_accessToken': '',
}
