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

from typing import cast

from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect
from django.template import TemplateDoesNotExist
from django.test import RequestFactory, override_settings

from webxiang import views
from webxiang.typing import Album


def test_display_redirects_to_canonical_url(sample_repo_settings, monkeypatch):
    request = RequestFactory().get('/album-one/')
    monkeypatch.setattr(
        views.webxiang,
        'get_data',
        lambda **kwargs: {
            'canonical_url': '/album-one/1',
            'meta': {'template': 'default.html'},
        },
    )

    response = views.display(request, album='album-one')

    assert isinstance(response, HttpResponsePermanentRedirect)
    assert response.url == '/album-one/1'


def test_display_falls_back_to_default_template(sample_repo_settings, monkeypatch):
    request = RequestFactory().get('/album-one/')
    rendered_templates: list[str] = []

    def fake_render(request, template_name, context):
        rendered_templates.append(template_name)
        if template_name == 'missing.html':
            raise TemplateDoesNotExist(template_name)
        return HttpResponse(template_name)

    monkeypatch.setattr(views, 'render', fake_render)
    monkeypatch.setattr(
        views.webxiang,
        'get_data',
        lambda **kwargs: {'meta': {'template': 'missing'}, 'entries': []},
    )

    response = views.display(request, album='album-one')

    assert response.content == b'default.html'
    assert rendered_templates == ['missing.html', 'default.html']


def test_display_raises_404_when_album_is_missing(sample_repo_settings, monkeypatch):
    request = RequestFactory().get('/missing/')
    monkeypatch.setattr(views.webxiang, 'get_data', lambda **kwargs: None)

    try:
        views.display(request, album='missing')
    except Http404 as exc:
        assert 'Album not found: missing' in str(exc)
    else:
        raise AssertionError('display() should raise Http404 for missing albums')


def test_display_builds_site_url_from_relative_setting(monkeypatch):
    request = RequestFactory().get('/album-one/', HTTP_X_SCHEME='https')
    seen: dict[str, object] = {}

    def fake_get_data(
        *, album, photo=None, page=1, site_url=None, is_mobile=False, **kwargs
    ):
        seen['site_url'] = site_url
        return {'meta': {'template': 'default.html'}, 'entries': []}

    monkeypatch.setattr(views.webxiang, 'get_data', fake_get_data)
    monkeypatch.setattr(
        views, 'render', lambda request, template_name, context: HttpResponse('ok')
    )

    with override_settings(SITE_URL='example.com'):
        views.display(request, album='album-one')

    assert seen['site_url'] == 'https://example.com'


def test_display_keeps_absolute_site_url_unchanged(monkeypatch):
    request = RequestFactory().get('/album-one/')
    seen: dict[str, object] = {}

    def fake_get_data(
        *, album, photo=None, page=1, site_url=None, is_mobile=False, **kwargs
    ):
        seen['site_url'] = site_url
        return {
            'meta': {'template': 'default.html', 'style': 'base.css'},
            'entries': [],
        }

    monkeypatch.setattr(views.webxiang, 'get_data', fake_get_data)
    monkeypatch.setattr(
        views, 'render', lambda request, template_name, context: HttpResponse('ok')
    )

    with override_settings(SITE_URL='https://cdn.example.org/gallery/'):
        views.display(request, album='album-one')

    assert seen['site_url'] == 'https://cdn.example.org/gallery/'


def test_onephoto_uses_year_from_photo_name(sample_repo_settings, monkeypatch):
    request = RequestFactory().get('/2024-summer.jpg')
    seen: dict[str, object] = {}

    def fake_render(request, template_name, context):
        seen['template'] = template_name
        seen['context'] = context
        return HttpResponse('ok')

    monkeypatch.setattr(views, 'render', fake_render)

    response = views.onephoto(request, '2024-summer.jpg')

    assert response.content == b'ok'
    assert seen['template'] == 'photo.html'
    context = cast(Album, seen['context'])
    assert context['meta']['copyright'] == '2024 Your Name'
    assert context['entry']['url'].endswith('/2024-summer.jpg')


def test_onephoto_joins_photos_base_url_without_trimming(
    sample_repo_settings, monkeypatch
):
    request = RequestFactory().get('/cover.jpg')
    seen: dict[str, object] = {}

    def fake_render(request, template_name, context):
        seen['context'] = context
        return HttpResponse('ok')

    monkeypatch.setattr(views, 'render', fake_render)

    with override_settings(WEBXIANG_PHOTOS_URL='https://cdn.example.org/data/'):
        views.onephoto(request, '2024/summer.jpg')

    context = cast(Album, seen['context'])
    assert context['entry']['url'] == 'https://cdn.example.org/data/2024/summer.jpg'


def test_onephoto_omits_year_when_photo_name_does_not_start_with_digits(
    sample_repo_settings, monkeypatch
):
    request = RequestFactory().get('/cover.jpg')
    seen: dict[str, object] = {}

    def fake_render(request, template_name, context):
        seen['context'] = context
        return HttpResponse('ok')

    monkeypatch.setattr(views, 'render', fake_render)

    views.onephoto(request, 'cover.jpg')

    context = cast(Album, seen['context'])
    assert context['meta']['copyright'] == ' Your Name'
