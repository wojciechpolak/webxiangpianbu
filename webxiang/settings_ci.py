"""
# CI/test settings for WebXiangpianbu.
"""

import os
import secrets

os.environ.setdefault('WEBXIANG_SECRET_KEY', secrets.token_urlsafe(32))

from .settings_sample import *  # noqa: F401,F403
