"""
# Django settings for WebXiangpianbu project (DOCKER VERSION).

Everything not overridden here comes from `webxiang.settings`, including
the environment variables it reads (set WEBXIANG_SECRET_KEY).
"""

from urllib.parse import urljoin

from webxiang.env import get_bool, get_env
from webxiang.settings import *  # noqa: F401,F403
from webxiang.settings import ALLOWED_HOSTS, ENV, PIPELINE

DEBUG = get_bool(ENV, 'DEBUG', 'APP_DEBUG', default=False)

ALLOWED_HOSTS = [*ALLOWED_HOSTS, 'backend']
if virtual_host := get_env(ENV, 'VIRTUAL_HOST'):
    ALLOWED_HOSTS.append(virtual_host)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': get_env(ENV, 'CACHE_LOCATION', default='memcached:11211'),
        'KEY_PREFIX': 'webxiang',
    },
}

VIRTUAL_PATH = get_env(ENV, 'VIRTUAL_PATH', default='/')

STATIC_URL = VIRTUAL_PATH + 'static/'
FORCE_SCRIPT_NAME = VIRTUAL_PATH

SITE_URL = get_env(ENV, 'SITE_URL', 'VIRTUAL_PATH', default='http://localhost:8080')
WEBXIANG_PHOTOS_URL = get_env(
    ENV, 'PHOTOS_BASE_URL', default=urljoin(SITE_URL, 'data/')
)

PIPELINE['COMPILERS'] = ('pipeline.compilers.sass.SASSCompiler',)
PIPELINE['SASS_BINARY'] = 'pysassc'
