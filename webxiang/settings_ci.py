"""
# CI/test settings for WebXiangpianbu.
"""

import os
import tempfile
import secrets

os.environ.setdefault('WEBXIANG_SECRET_KEY', secrets.token_urlsafe(32))

from .settings_sample import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(tempfile.gettempdir(), 'webxiang-tests.sqlite3'),
    }
}
