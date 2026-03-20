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
import json

import pytest
from django.core.cache.backends.locmem import LocMemCache
from django.test import override_settings

from webxiang import webxiang


def test_open_albumfile_reads_sample_json(sample_repo_settings):
    data = webxiang._open_albumfile('album-one')

    assert data is not None
    assert data['meta']['title'] == 'Fireworks'
    assert len(data['entries']) == 3


def test_open_albumfile_prefers_yaml_when_both_exist(tmp_path, monkeypatch):
    album_dir = tmp_path / 'albums'
    album_dir.mkdir()
    (album_dir / 'sample.json').write_text(
        json.dumps({'meta': {'title': 'json'}, 'entries': []}),
        encoding='utf-8',
    )
    (album_dir / 'sample.yaml').write_text(
        'meta:\n  title: yaml\nentries: []\n',
        encoding='utf-8',
    )

    with override_settings(ALBUM_DIR=str(album_dir)):
        cache = LocMemCache('open-albumfile', {})
        monkeypatch.setattr(webxiang, 'cache', cache)

        data = webxiang._open_albumfile('sample')

    assert data is not None
    assert data['meta']['title'] == 'yaml'


def test_open_albumfile_uses_cache_when_file_changes(tmp_path, monkeypatch):
    album_dir = tmp_path / 'albums'
    album_dir.mkdir()
    album_file = album_dir / 'cached.json'
    album_file.write_text(
        json.dumps({'meta': {'title': 'first'}, 'entries': []}),
        encoding='utf-8',
    )

    cache_store: dict[str, dict[str, object]] = {}

    class FakeCache:
        def get(self, key):
            return cache_store.get(key)

        def set(self, key, value, timeout=None):
            cache_store[key] = value

    with override_settings(ALBUM_DIR=str(album_dir)):
        monkeypatch.setattr(webxiang, 'cache', FakeCache())
        first = webxiang._open_albumfile('cached')
        assert first is not None
        assert first['meta']['title'] == 'first'

        cache_store['album:cached']['mtime'] = 10**12
        album_file.write_text(
            json.dumps({'meta': {'title': 'second'}, 'entries': []}),
            encoding='utf-8',
        )

        second = webxiang._open_albumfile('cached')

    assert second is first
    assert second['meta']['title'] == 'first'


def test_open_albumfile_missing_returns_none(tmp_path):
    with override_settings(ALBUM_DIR=str(tmp_path)):
        assert webxiang._open_albumfile('missing') is None


@pytest.mark.parametrize(
    ('video', 'expected_type', 'expected_vid'),
    [
        ('https://www.youtube.com/watch?v=abc123', 'youtube', 'abc123'),
        ('https://vimeo.com/987654', 'vimeo', '987654'),
        (
            'https://example.com/movie.mp4',
            'html5',
            [{'src': 'https://example.com/movie.mp4', 'type': 'video/mp4'}],
        ),
    ],
)
def test_parse_video_entry_handles_common_video_types(
    video, expected_type, expected_vid
):
    entry = {'video': video}

    webxiang._parse_video_entry(entry)

    assert entry['type'] == expected_type
    assert entry['vid'] == expected_vid


def test_parse_video_entry_preserves_multiple_html5_sources():
    entry = {
        'video': [
            'https://example.com/movie.mp4',
            {'src': 'https://example.com/movie.webm', 'media': '(max-width: 600px)'},
        ]
    }

    webxiang._parse_video_entry(entry)

    assert entry['type'] == 'html5'
    assert entry['vid'][0] == {
        'src': 'https://example.com/movie.mp4',
        'type': 'video/mp4',
    }
    assert entry['vid'][1] == {
        'src': 'https://example.com/movie.webm',
        'media': '(max-width: 600px)',
    }


@pytest.mark.parametrize(
    ('photo', 'expected_title', 'expected_url', 'expected_next', 'expected_prev'),
    [
        (
            '1',
            '#1 - Fireworks',
            '/data/2007-01-fireworks/dsc08340.jpg',
            '/album-one/2',
            None,
        ),
        (
            '1/dsc08340',
            '#1 - Fireworks',
            '/data/2007-01-fireworks/dsc08340.jpg',
            '/album-one/2',
            None,
        ),
        (
            '3',
            '#3 - Fireworks',
            '/data/2007-01-fireworks/dsc08340.jpg',
            None,
            '/album-one/2',
        ),
    ],
)
def test_get_data_photo_context_uses_sample_album(
    sample_repo_settings,
    photo,
    expected_title,
    expected_url,
    expected_next,
    expected_prev,
):
    data = webxiang.get_data('album-one', photo=photo)

    assert data is not None
    assert data['mode'] == 'photo'
    assert data['meta']['title'] == expected_title
    assert data['canonical_url'] == f'/album-one/{photo.split("/")[0]}'
    assert data['entry']['url'] == expected_url
    assert data['entry']['link'] == '/album-one/'
    assert data['next_entry'] == expected_next
    assert data['prev_entry'] == expected_prev


def test_get_data_album_context_uses_sample_data(sample_repo_settings):
    index_data = webxiang.get_data('index')
    album_data = webxiang.get_data('album-one')

    assert index_data is not None
    assert index_data['mode'] == 'album'
    assert index_data['meta']['title'] == 'Photo Albums'
    assert index_data['meta']['style'] == 'light.css'
    assert len(index_data['entries']) == 1

    assert album_data is not None
    assert album_data['mode'] == 'album'
    assert album_data['meta']['title'] == 'Fireworks'
    assert (
        album_data['meta']['cover'] == '/data/2007-01-fireworks/tiny/tiny-dsc08340.jpg'
    )
    assert len(album_data['entries']) == 3

    groups = [list(group) for group in album_data['groups']]
    assert len(groups) == 1
    assert len(groups[0]) == 3
    assert groups[0][0]['url'] == '/data/2007-01-fireworks/tiny/tiny-dsc08340.jpg'


def test_get_data_missing_photo_returns_none(sample_repo_settings):
    assert webxiang.get_data('album-one', photo='99') is None


def test_get_data_mobile_story_template_switches_to_floating(monkeypatch):
    album = {
        'meta': {
            'template': 'story',
            'title': 'Story Album',
            'ppp': 4,
            'columns': 2,
            'thumbs_skip': True,
        },
        'entries': [
            {'image': 'one.jpg'},
            {'image': 'two.jpg'},
        ],
    }

    monkeypatch.setattr(webxiang, '_open_albumfile', lambda album_name: album)
    data = webxiang.get_data('story-album', is_mobile=True)

    assert data is not None
    assert data['meta']['template'] == 'floating'
    assert data['meta']['thumbs_skip'] is False


def test_get_data_reverse_order_flips_navigation_and_canonical(monkeypatch):
    album = {
        'meta': {
            'title': 'Reverse Album',
            'ppp': 2,
            'columns': 2,
            'reverse_order': True,
        },
        'entries': [
            {'image': 'first.jpg', 'slug': 'first'},
            {'image': 'second.jpg', 'slug': 'second'},
            {'image': 'third.jpg', 'slug': 'third'},
        ],
    }

    monkeypatch.setattr(
        webxiang, '_open_albumfile', lambda album_name: copy.deepcopy(album)
    )
    data = webxiang.get_data('reverse-album', photo='2')

    assert data is not None
    assert data['meta']['title'] == '#2 - Reverse Album'
    assert data['canonical_url'] == '/reverse-album/2/second'
    assert data['entry']['image'] == 'second.jpg'
    assert data['next_entry'] == '/reverse-album/1/first'
    assert data['prev_entry'] == '/reverse-album/3/third'


def test_get_data_relative_links_switch_photo_navigation(monkeypatch):
    album = {
        'meta': {
            'title': 'Relative Album',
            'ppp': 2,
            'columns': 2,
        },
        'entries': [
            {'image': 'first.jpg'},
            {'image': 'second.jpg'},
            {'image': 'third.jpg'},
        ],
    }

    monkeypatch.setattr(
        webxiang, '_open_albumfile', lambda album_name: copy.deepcopy(album)
    )
    with override_settings(ROOT_URLCONF='webxiang.urls_static'):
        data = webxiang.get_data('relative-album', photo='2', relative_links=True)

    assert data is not None
    assert data['entry']['link'] == 'index.html'
    assert data['prev_entry'] == '1.html'
    assert data['next_entry'] == '3.html'


def test_get_data_story_prev_and_next_story_links(monkeypatch):
    album = {
        'meta': {
            'title': 'Story Album',
            'ppp': 2,
            'columns': 2,
            'prev_story': 'prev-album',
            'next_story': '/stories/next-album/',
        },
        'entries': [{'image': 'one.jpg'}],
    }

    monkeypatch.setattr(
        webxiang, '_open_albumfile', lambda album_name: copy.deepcopy(album)
    )
    data = webxiang.get_data('story-album')

    assert data is not None
    assert data['prev_story'] == '/prev-album/'
    assert data['next_story'] == '/stories/next-album/'


def test_get_data_appends_css_and_joins_cover_with_site_url(
    sample_repo_settings, monkeypatch
):
    album = {
        'meta': {
            'title': 'Cover Album',
            'style': 'midnight',
            'cover': 'covers/front.jpg',
            'path': 'photos/',
            'ppp': 2,
            'columns': 2,
        },
        'entries': [{'image': 'one.jpg'}],
    }

    monkeypatch.setattr(
        webxiang, '_open_albumfile', lambda album_name: copy.deepcopy(album)
    )
    data = webxiang.get_data('cover-album', site_url='https://example.org/base/')

    assert data is not None
    assert data['meta']['style'] == 'midnight.css'
    assert data['meta']['cover'] == 'https://example.org/data/photos/covers/front.jpg'


def test_get_data_limits_page_range_for_large_albums(monkeypatch):
    album = {
        'meta': {
            'title': 'Paged Album',
            'ppp': 5,
            'columns': 2,
        },
        'entries': [{'image': f'{idx}.jpg'} for idx in range(1, 101)],
    }

    monkeypatch.setattr(
        webxiang, '_open_albumfile', lambda album_name: copy.deepcopy(album)
    )
    data = webxiang.get_data('paged-album', page=10)

    assert data is not None
    assert data['entries'].number == 10
    assert list(data['entries'].paginator.page_range_limited) == list(range(4, 16))


def test_get_data_geomap_collects_geo_points(sample_repo_settings, monkeypatch):
    album = {
        'meta': {
            'title': 'Geo Album',
            'ppp': 2,
            'columns': 2,
        },
        'entries': [
            {'image': 'one.jpg', 'geo': (50.1, 19.9), 'exif': {'keep': 'no'}},
            {'image': 'two.jpg', 'geo': (50.1, 19.9)},
            {'image': 'three.jpg', 'geo': (51.0, 20.0)},
        ],
    }

    monkeypatch.setattr(webxiang, '_open_albumfile', lambda album_name: album)
    data = webxiang.get_data('geo-album', photo='geomap')

    assert data is not None
    assert data['mode'] == 'geomap'
    assert data['meta']['ppp'] == 500
    assert 'entries' not in data

    settings_data = json.loads(data['wxpb_settings'])
    assert settings_data['geo_points'][0][0] == [50.1, 19.9]
    assert settings_data['geo_points'][1][0] == [51.0, 20.0]
    assert [entry['index'] for entry in settings_data['geo_points'][0][1]] == [1, 2]
    assert [entry['index'] for entry in settings_data['geo_points'][1][1]] == [3]
    assert all(
        'exif' not in entry
        for _, entries in settings_data['geo_points']
        for entry in entries
    )
