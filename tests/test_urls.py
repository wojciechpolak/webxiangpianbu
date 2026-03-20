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

from django.test import override_settings
from django.urls import resolve


def test_dynamic_urlconf_resolves_album_and_photo_routes():
    assert resolve('/album-one/').url_name == 'album'
    assert resolve('/album-one/1/dsc08340').url_name == 'photo'
    assert resolve('/1.jpg').url_name == 'onephoto'


def test_static_urlconf_resolves_relative_photo_route():
    with override_settings(ROOT_URLCONF='webxiang.urls_static'):
        assert resolve('/2.html').url_name == 'photo_relative'
        assert resolve('/album-one/2.html').url_name == 'photo'
