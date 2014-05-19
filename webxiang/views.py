#  WebXiangpianbu Copyright (C) 2013, 2014 Wojciech Polak
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

import urlparse

from django.conf import settings
from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import render
from django.template import TemplateDoesNotExist

from . import webxiang


def display(request, album='index', photo=None):
    if hasattr(settings, 'SITE_URL'):
        if not settings.SITE_URL.startswith('http'):
            site_url = '%s://%s' % \
                (request.META.get('HTTP_X_SCHEME', 'http'),
                 settings.SITE_URL)
        else:
            site_url = settings.SITE_URL
    else:
        site_url = None

    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    is_mobile = ('Mobi' in request.META.get('HTTP_USER_AGENT', '') or
                 request.GET.get('mobile'))

    data = webxiang.get_data(album=album, photo=photo, page=page,
                             site_url=site_url, is_mobile=is_mobile)
    if not data:
        raise Http404
    elif 'canonical_url' in data \
            and data['canonical_url'] != request.path:
        return HttpResponsePermanentRedirect(data['canonical_url'])

    tpl = data['meta'].get('template') or 'default.html'
    if not tpl.endswith('.html'):
        tpl += '.html'

    try:
        return render(request, tpl, data)
    except TemplateDoesNotExist:
        return render(request, 'default.html', data)


def onephoto(request, photo):
    baseurl = settings.WEBXIANG_PHOTOS_URL
    year = photo[:4]
    if not year.isdigit():
        year = ''
    ctx = {
        'meta': {
            'style': 'photo.css',
            'copyright': '%s %s' % (year, getattr(settings, 'COPYRIGHT_OWNER',
                                                  '')),
        },
        'entry': {
            'url': urlparse.urljoin(baseurl, photo),
        },
    }
    return render(request, 'photo.html', ctx)
