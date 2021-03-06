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

from django.conf.urls import url
from webxiang import views

urlpatterns = [
    url(r'^$', views.display, name='index'),
    url(r'^(?P<photo>[\w-]+\.jpg)$', views.onephoto, name='onephoto'),
    url(r'^(?P<album>[\w-]+)/$', views.display, name='album'),
    url(r'^(?P<album>[\w-]+)/(?P<photo>[\w\-\./]+)\.html$', views.display,
        name='photo'),
]
