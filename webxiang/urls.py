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

from django.conf import settings
from django.conf.urls import patterns, url
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = static(settings.WEBXIANG_PHOTOS_URL,
                     document_root=settings.WEBXIANG_PHOTOS_ROOT)

urlpatterns += staticfiles_urlpatterns()

urlpatterns += patterns(
    'webxiang',
    url(r'^$', 'views.display', name='index'),
    url(r'^(?P<photo>[\w-]+\.jpg)$', 'views.onephoto', name='onephoto'),
    url(r'^(?P<album>[\w-]+)/$', 'views.display', name='album'),
    url(r'^(?P<album>[\w-]+)/(?P<photo>[\w\-\./]+)$', 'views.display',
        name='photo'),
)
