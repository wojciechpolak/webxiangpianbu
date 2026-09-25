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

from django.template.loader import render_to_string

from webxiang.templatetags.embed import embed, gen_video_source
from webxiang.templatetags.page import page
from webxiang.webxiang import _paginate, get_data


def test_page_tag_uses_query_string_for_dynamic_urls():
    assert page({}, 'album-one', '/album-one/', 1) == '/album-one/'
    assert page({}, 'album-one', '/album-one/', 2) == '?page=2'


def test_page_tag_switches_to_static_urls(monkeypatch):
    monkeypatch.setattr(
        'webxiang.templatetags.page.get_urlconf', lambda: 'webxiang.urls_static'
    )

    assert page({}, 'album-one', '/album-one/', 1) == '/album-one/'
    assert page({}, 'album-one', '/album-one/', 3) == '/album-one/page-3.html'


def test_gen_video_source_includes_optional_attributes():
    html = gen_video_source(
        {'src': '/movie.webm', 'media': '(min-width: 600px)', 'type': 'video/webm'}
    )

    assert (
        html
        == '<source src="/movie.webm" media="(min-width: 600px)" type="video/webm">'
    )


def test_embed_renders_youtube_iframe():
    html = embed({'video': True, 'type': 'youtube', 'vid': 'abc123'})

    assert 'youtube.com/embed/abc123' in html
    assert '<iframe' in html


def test_embed_renders_vimeo_iframe():
    html = embed({'video': True, 'type': 'vimeo', 'vid': '987654'})

    assert 'player.vimeo.com/video/987654' in html
    assert 'vimeo' in html


def test_embed_renders_html5_video_and_download_link():
    html = embed(
        {
            'video': True,
            'type': 'html5',
            'vid': [
                {'src': '/movie.mp4', 'type': 'video/mp4'},
                {
                    'src': '/movie.webm',
                    'media': '(min-width: 600px)',
                    'type': 'video/webm',
                },
            ],
            'poster': '/poster.jpg',
            'video_autoplay': True,
            'video_preload': True,
            'video_download': '/download/movie.mp4',
        }
    )

    assert '<video controls poster="/poster.jpg" autoplay preload="auto">' in html
    assert '<source src="/movie.mp4" type="video/mp4">' in html
    assert (
        '<source src="/movie.webm" media="(min-width: 600px)" type="video/webm">'
        in html
    )
    assert 'href="/download/movie.mp4"' in html


def test_embed_gives_iframes_a_title():
    youtube = embed({'video': True, 'type': 'youtube', 'vid': 'abc'})
    vimeo = embed(
        {'video': True, 'type': 'vimeo', 'vid': '1', 'title': 'A "quoted" <clip>'}
    )

    assert 'title="YouTube video"' in youtube
    assert 'title="A &quot;quoted&quot; &lt;clip&gt;"' in vimeo


def test_pages_partial_marks_current_page(sample_repo_settings):
    entries = _paginate([{'index': i} for i in range(1, 4)], 1, 2)
    html = render_to_string('_pages.html', {'entries': entries, 'album': 'album-one'})
    bottom = render_to_string(
        '_pages.html',
        {'entries': entries, 'album': 'album-one', 'pages_bottom': True},
    )

    assert '<nav class="pages" aria-label="Pages">' in html
    assert '<span class="thisPage" aria-current="page">2</span>' in html
    assert 'aria-label="Page 3"' in html
    assert 'id="prevPage"' in html and 'id="nextPage"' in html
    assert 'aria-label="Pages (bottom)"' in bottom
    assert 'id="prevPage"' not in bottom and 'id="nextPage"' not in bottom


def test_album_page_has_landmarks_and_lang(sample_repo_settings):
    data = get_data('album-one')
    assert data is not None
    data['meta']['lang'] = 'pl'

    html = render_to_string('default.html', cast(dict, data))

    assert '<html lang="pl">' in html
    assert '<a class="skip-link" href="#main">' in html
    for tag in ('<header>', '<nav id="menu"', '<main id="main">', '<footer>'):
        assert tag in html
    assert '<h1 id="title">Fireworks</h1>' in html
    assert 'alt="Photo 1"' in html
    assert 'role="dialog"' in html
