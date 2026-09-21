"""
# CI/test settings for WebXiangpianbu.

Ignores the developer's `.env` and `settings_local.py` so tests stay hermetic.
"""

import os
import secrets
import tempfile

os.environ.setdefault('WEBXIANG_LOAD_DOTENV', '0')
os.environ.setdefault('WEBXIANG_SETTINGS_LOCAL', '0')
os.environ.setdefault('WEBXIANG_SECRET_KEY', secrets.token_urlsafe(32))

from .settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(tempfile.gettempdir(), 'webxiang-tests.sqlite3'),
    }
}
