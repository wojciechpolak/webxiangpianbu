#  WebXiangpianbu Copyright (C) 2014 Wojciech Polak
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
#  with this program.  If not, see <http://www.gnu.org/licenses/>.

from django import template
from django.core.urlresolvers import get_urlconf
from django.utils.translation import ugettext as _

register = template.Library()


@register.simple_tag(takes_context=True)
def page(context, album_name, album_url, page_number):
    if get_urlconf() == 'webxiang.urls_static':
        if page_number > 1:
            # Translators: this is an URL
            return _('page-%(number)s.html') % {'number': page_number}
        else:
            return 'index.html'
    else:
        if page_number > 1:
            return '?page=%s' % page_number
        else:
            return album_url
