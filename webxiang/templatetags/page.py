"""
#  WebXiangpianbu Copyright (C) 2014, 2023 Wojciech Polak
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

from typing import Any

from django import template
from django.urls import get_urlconf
from django.utils.translation import gettext as _

register = template.Library()


@register.simple_tag(takes_context=True)
def page(
    context: dict[str, Any], album_name: str, album_url: str, page_number: int
) -> str:
    if page_number <= 1:
        return album_url
    if get_urlconf() == 'webxiang.urls_static':
        # Translators: this is an URL
        return album_url + _('page-%(number)s.html') % {'number': page_number}
    return f'?page={page_number}'
