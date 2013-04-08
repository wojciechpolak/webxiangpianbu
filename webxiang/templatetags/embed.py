#  WebXiangpianbu Copyright (C) 2013 Wojciech Polak
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
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def embed(entry):
    s = ''
    if entry['video']:
        if entry['type'] == 'youtube':
            s = '<div class="video"><iframe width="853" height="480" src="//www.youtube.com/embed/%s?rel=0" frameborder="0" allowfullscreen></iframe></div>' % entry['vid']
        elif entry['type'] == 'vimeo':
            s = '<div class="video vimeo"><iframe width="854" height="480" src="//player.vimeo.com/video/%s" frameborder="0" allowfullscreen></iframe></div>' % entry['vid']
    return mark_safe(s)
