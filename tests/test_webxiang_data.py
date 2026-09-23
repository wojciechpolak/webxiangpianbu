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
import logging
from typing import Any, cast

import pytest
from django.conf import settings as django_settings
from django.core.cache.backends.locmem import LocMemCache
from django.core.paginator import Page
from django.test import override_settings
from django.urls import set_urlconf

from webxiang import webxiang
from webxiang.typing import Entry


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
    ('filename', 'content'), [('broken.json', '{'), ('broken.yaml', 'meta: [')]
)
def test_open_albumfile_logs_malformed_files(
    tmp_path, monkeypatch, caplog, filename, content
):
    (tmp_path / filename).write_text(content, encoding='utf-8')
    # a plain logger, independent of how LOGGING configured 'main'
    monkeypatch.setattr(webxiang, 'logger', logging.getLogger('tests.webxiang'))

    with override_settings(ALBUM_DIR=str(tmp_path)):
        monkeypatch.setattr(webxiang, 'cache', LocMemCache('malformed', {}))
        assert webxiang._open_albumfile('broken') is None

    (record,) = caplog.records
    assert record.levelname == 'ERROR'
    assert record.getMessage().startswith(
        f'cannot load album file {tmp_path / filename}: '
    )


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
    video: str, expected_type: str, expected_vid: object
):
    entry: dict[str, object] = {'video': video}

    webxiang._parse_video_entry(cast(Entry, entry))

    assert entry['type'] == expected_type
    assert entry['vid'] == expected_vid


def test_parse_video_entry_preserves_multiple_html5_sources():
    entry: dict[str, object] = {
        'video': [
            'https://example.com/movie.mp4',
            {'src': 'https://example.com/movie.webm', 'media': '(max-width: 600px)'},
        ]
    }

    webxiang._parse_video_entry(cast(Entry, entry))

    assert entry['type'] == 'html5'
    vid = cast(list[dict[str, Any]], entry['vid'])
    assert vid[0] == {
        'src': 'https://example.com/movie.mp4',
        'type': 'video/mp4',
    }
    assert vid[1] == {
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


def test_get_data_static_photo_links_back_to_its_album_page(monkeypatch):
    album = {
        'meta': {'title': 'Static Album', 'ppp': 2, 'columns': 2},
        'entries': [
            {'image': 'first.jpg'},
            {'image': 'second.jpg'},
            {'image': 'third.jpg'},
        ],
    }

    monkeypatch.setattr(
        webxiang, '_open_albumfile', lambda album_name: copy.deepcopy(album)
    )
    set_urlconf('webxiang.urls_static')
    try:
        data = webxiang.get_data('static-album', photo='3', staticgen=True)
    finally:
        set_urlconf(None)

    assert data is not None
    assert data['entry']['link'] == '/static-album/page-2.html'
    assert data['prev_entry'] == '/static-album/2.html'
    assert data['next_entry'] is None


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
    entries = cast(Page[Entry], data['entries'])
    assert entries.number == 10
    assert list(cast(Any, entries.paginator).page_range_limited) == list(range(4, 16))


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


@pytest.mark.parametrize(
    ('video', 'expected'),
    [
        ('movie.mp4', 'video/mp4'),
        ('movie.webm', 'video/webm'),
        ('movie.ogg', 'video/ogg'),
        ('movie.mov', 'video/quicktime'),
        ('movie.avi', 'video'),
    ],
)
def test_get_mtype_maps_extension_to_mime_type(video, expected):
    assert webxiang._get_mtype(video) == expected


@pytest.mark.parametrize(
    ('entry', 'expected'),
    [
        ({'image': 'one.jpg'}, 'one.jpg'),
        ({'image': {'file': 'two.jpg'}}, 'two.jpg'),
        ({'video': 'clip.mp4'}, 'clip.mp4'),
        ({'video': ['clip.webm', 'clip.mp4']}, 'clip.webm'),
        ({'video': [{'src': 'clip.ogg'}]}, 'clip.ogg'),
        ({'video': []}, None),
        ({'video': True}, None),
        ({'album': 'other'}, None),
    ],
)
def test_entry_filename_picks_image_or_first_video(entry, expected):
    assert webxiang._entry_filename(cast(Entry, entry)) == expected


FILENAME_ALBUM: dict[str, Any] = {
    'meta': {'title': 'Files', 'ppp': 2, 'columns': 2, 'path': 'p/'},
    'entries': [
        {'album': 'nested'},
        {'image': 'one.jpg', 'slug': 'one'},
        {'image': {'file': 'two.jpg', 'path': 'q/', 'size': [10, 20]}},
        {'video': ['clip.webm', {'src': 'clip.mp4'}]},
    ],
}


@pytest.mark.parametrize(
    ('photo', 'reverse_order', 'expected_idx'),
    [
        ('one', False, 2),
        ('one.jpg', False, 2),
        ('ONE.JPG', False, None),
        ('two.jpg', False, 3),
        ('clip.webm', False, None),  # '.jpg' gets appended
        ('one', True, 2),
        ('two', True, 3),
        ('missing', False, None),
        ('0', False, None),
        ('5', False, None),
        ('4/some-slug', False, 4),
    ],
)
def test_get_data_finds_photo_by_number_or_filename(
    monkeypatch, photo, reverse_order, expected_idx
):
    album = copy.deepcopy(FILENAME_ALBUM)
    album['meta']['reverse_order'] = reverse_order
    monkeypatch.setattr(webxiang, '_open_albumfile', lambda album_name: album)

    data = webxiang.get_data('files', photo=photo)

    if expected_idx is None:
        assert data is None
    else:
        assert data is not None
        assert data['entry']['index'] == expected_idx


def test_get_data_photo_with_image_dict_uses_its_path_and_size(monkeypatch):
    album = copy.deepcopy(FILENAME_ALBUM)
    monkeypatch.setattr(webxiang, '_open_albumfile', lambda album_name: album)

    data = webxiang.get_data('files', photo='3')

    assert data is not None
    assert data['entry']['url'] == '/data/q/two.jpg'
    assert data['entry']['size'] == [10, 20]
    # third photo, two per page
    assert data['entry']['link'] == '/files/?page=2'
    assert data['prev_entry'] == '/files/2/one'
    assert data['next_entry'] == '/files/4'


def test_get_data_photo_with_video_parses_sources(monkeypatch):
    album = copy.deepcopy(FILENAME_ALBUM)
    monkeypatch.setattr(webxiang, '_open_albumfile', lambda album_name: album)

    data = webxiang.get_data('files', photo='4', staticgen=True)

    assert data is not None
    entry = data['entry']
    assert entry['type'] == 'html5'
    assert entry['vid'] == [
        {'src': 'clip.webm', 'type': 'video/webm'},
        {'src': 'clip.mp4'},
    ]
    assert entry['url'] == '/data/'
    assert entry['size'] == ''


def test_get_data_photo_uses_entry_copyright_and_description(monkeypatch):
    album = {
        'meta': {'title': '', 'copyright': 'album', 'copyright_link': '/a/'},
        'entries': [
            {'image': 'one.jpg', 'geo': '1,2', 'exif': {'Make': 'X'}},
            {
                'image': 'two.jpg',
                'description': 'Two',
                'copyright': 'photo',
                'copyright_link': '/p/',
            },
        ],
    }
    monkeypatch.setattr(
        webxiang, '_open_albumfile', lambda album_name: copy.deepcopy(album)
    )

    first = webxiang.get_data('untitled', photo='1')
    second = webxiang.get_data('untitled', photo='2')

    assert first is not None
    assert first['meta']['title'] == '#1 - untitled'
    assert first['meta']['description'] == '#1 - untitled'
    assert first['meta']['copyright'] == 'album'
    assert first['meta']['copyright_link'] == '/a/'
    assert 'exif' not in first['entry']
    assert json.loads(first['wxpb_settings'])['geo_points'][0][0] == '1,2'

    assert second is not None
    assert second['meta']['description'] == 'Two'
    assert second['meta']['copyright'] == 'photo'
    assert second['meta']['copyright_link'] == '/p/'
    assert json.loads(second['wxpb_settings'])['geo_points'] == []


def test_get_data_wxpb_settings_does_not_leak_between_albums(monkeypatch):
    album = {
        'meta': {'title': 'Custom map'},
        'entries': [{'image': 'one.jpg', 'geo': '1,2'}],
    }
    monkeypatch.setattr(webxiang, '_open_albumfile', lambda album_name: album)

    with override_settings(WXPB_SETTINGS={'plugin': 'leaflet'}):
        data = webxiang.get_data('custom', photo='1')
        assert django_settings.WXPB_SETTINGS == {'plugin': 'leaflet'}

    assert data is not None
    wxpb_settings = json.loads(data['wxpb_settings'])
    assert wxpb_settings['plugin'] == 'leaflet'
    assert wxpb_settings['geo_points'][0][0] == '1,2'


def test_get_data_album_entries_get_thumbs_links_and_videos(monkeypatch):
    album = {
        'meta': {
            'title': 'Mixed',
            'path': 'p/',
            'path_thumb': 'p/t/',
            'ppp': 10,
            'columns': 0,
            'default_thumb_size': [5, 5],
        },
        'entries': [
            {'image': 'one.jpg', 'thumb': 'tone.jpg', 'slug': 'one'},
            {
                'image': {'file': 'two.jpg'},
                'thumb': {'file': 'ttwo.jpg', 'path': 'x/', 'size': [1, 2]},
            },
            {'image': 'three.jpg', 'link': '/custom/'},
            {'album': 'other', 'thumb': 'cover.jpg'},
            {'video': 'https://vimeo.com/123'},
        ],
    }
    monkeypatch.setattr(webxiang, '_open_albumfile', lambda album_name: album)

    data = webxiang.get_data('mixed')

    assert data is not None
    assert 'groups' not in data
    one, two, three, other, video = cast(Page[Entry], data['entries']).object_list
    assert one['url_full'] == '/data/p/one.jpg'
    assert one['url'] == '/data/p/t/tone.jpg'
    assert one['size'] == [5, 5]
    assert one['link'] == '/mixed/1/one'
    assert two['url_full'] == '/data/p/two.jpg'
    assert two['url'] == '/data/x/ttwo.jpg'
    assert two['size'] == [1, 2]
    assert two['link'] == '/mixed/2'
    assert three['link'] == '/custom/'
    assert other['link'] == '/other/'
    assert video['type'] == 'vimeo'
    assert 'url' not in video


def test_get_data_album_thumbs_skip_uses_full_images(monkeypatch):
    album = {
        'meta': {
            'path': 'p/',
            'path_thumb': 'p/t/',
            'thumbs_skip': True,
            'default_image_size': [8, 6],
            'cover': 'cover.jpg',
        },
        'entries': [
            {'image': 'one.jpg', 'thumb': 'tone.jpg'},
            {'image': {'file': 'two.jpg', 'size': [3, 4]}},
        ],
    }
    monkeypatch.setattr(webxiang, '_open_albumfile', lambda album_name: album)

    data = webxiang.get_data('skip', staticgen=True)

    assert data is not None
    one, two = cast(Page[Entry], data['entries']).object_list
    assert one['url'] == '/data/one.jpg'
    assert one['size'] == [8, 6]
    assert two['url'] == '/data/two.jpg'
    assert two['size'] == [3, 4]
    # the cover is resolved against the last entry's directory
    assert data['meta']['cover'] == '/data/cover.jpg'


def test_get_data_empty_album_resolves_cover_against_album_path(monkeypatch):
    album = {'meta': {'path': 'p/', 'cover': 'cover.jpg'}, 'entries': []}
    monkeypatch.setattr(webxiang, '_open_albumfile', lambda album_name: album)

    data = webxiang.get_data('empty', page=3)

    assert data is not None
    assert cast(Page[Entry], data['entries']).number == 1
    assert data['meta']['cover'] == '/data/p/cover.jpg'


def test_get_data_missing_album_returns_none(monkeypatch):
    monkeypatch.setattr(webxiang, '_open_albumfile', lambda album_name: None)

    assert webxiang.get_data('missing') is None
