"""
#  WebXiangpianbu Copyright (C) 2026 Wojciech Polak
#
#  This program is free software; you can redistribute it and/or modify it
#  under the terms of the GNU General Public License as published by the
#  Free Software Foundation; either version 3 of the License, or (at your
#  option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
from django.conf import settings as django_settings
from django.test import override_settings

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_ALBUM_DIR = ROOT / 'run' / 'albums'
SAMPLE_PHOTO_ROOT = ROOT / 'run' / 'data'


@pytest.fixture
def sample_repo_settings():
    with override_settings(
        ALBUM_DIR=str(SAMPLE_ALBUM_DIR),
        WEBXIANG_PHOTOS_ROOT=str(SAMPLE_PHOTO_ROOT),
        WEBXIANG_PHOTOS_URL='/data/',
        SITE_URL='https://www.example.org/',
        WXPB_SETTINGS=copy.deepcopy(getattr(django_settings, 'WXPB_SETTINGS', {})),
    ):
        yield
