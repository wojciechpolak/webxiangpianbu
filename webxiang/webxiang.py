"""
#  WebXiangpianbu Copyright (C) 2013, 2014, 2015, 2023 Wojciech Polak
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

import html
import json
import logging
import os
import re
from dataclasses import dataclass
from itertools import zip_longest
from typing import Any, cast
from urllib.parse import urljoin

from django.conf import settings
from django.core.cache import cache
from django.core.paginator import EmptyPage, InvalidPage, Page, Paginator
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.utils.translation import gettext as _

from .templatetags.page import page as page_url
from .typing import Album, Entry, Image, MetaData, VideoSrc

yaml: Any = None
YamlLoader: Any = None

try:
    import yaml as _yaml

    yaml = _yaml

    YamlLoader = cast(Any, getattr(_yaml, 'CLoader', _yaml.Loader))
except ImportError:
    yaml = None

logger = logging.getLogger('main')


@dataclass(frozen=True)
class _Links:
    """How URLs are built for one `get_data` call."""

    album: str
    baseurl: str
    staticgen: bool

    def photo(self, link: str | int) -> str:
        return reverse('photo', kwargs={'album': self.album, 'photo': link})

    def media_dir(self, path: str) -> str:
        return self.baseurl if self.staticgen else urljoin(self.baseurl, path)


def get_data(
    album: str,
    photo: str | None = None,
    page: int = 1,
    site_url: str | None = None,
    is_mobile: bool = False,
    staticgen: bool = False,
) -> Album | None:
    album_data = _open_albumfile(album)
    if not album_data:
        return None

    data = _init_data(album, album_data, is_mobile)
    meta = data['meta']
    links = _Links(album, data['URL_PHOTOS'], staticgen)

    if photo and photo != 'geomap':
        mode = 'photo'
        path = _photo_context(data, links, photo)
        if path is None:
            return None
    else:
        mode = 'geomap' if photo == 'geomap' else 'album'
        path = _album_context(data, links, page, geomap=mode == 'geomap')

    if meta['style'] and not meta['style'].endswith('.css'):
        meta['style'] += '.css'
    meta['cover'] = _cover_url(meta['cover'], path, site_url)

    ctx: Album = {
        'mode': mode,
        'album': album,
    }
    ctx.update(data)

    return ctx


def _init_data(album: str, album_data: Album, is_mobile: bool) -> Album:
    """Album defaults merged with the album file, entries numbered from 1."""
    data: Album = {
        'STATIC_URL': getattr(settings, 'STATIC_URL', ''),
        'URL_PHOTOS': getattr(settings, 'WEBXIANG_PHOTOS_URL', 'data/'),
        'meta': {
            'template': 'default.html',
            'style': 'base.css',
            'title': 'Albums',
            'robots': 'noindex,nofollow',
            'custom_menu': False,
            'columns': 3,
            'ppp': 36,
            'reverse_order': False,
            'default_thumb_size': (180, 180),
            'cover': None,
        },
        'entries': [],
    }
    meta = data['meta']
    meta.update(album_data.get('meta', {}))
    meta['title_gallery'] = meta['title'] or album

    # force mobile template
    if meta['template'] == 'story' and is_mobile:
        meta['template'] = 'floating'
        meta['thumbs_skip'] = False

    entries = cast(list[Entry], album_data.get('entries', []))
    for i, entry in enumerate(entries, start=1):
        entry['index'] = i
    if meta['reverse_order']:
        entries = list(reversed(entries))
    data['entries'] = entries
    return data


def _photo_context(data: Album, links: _Links, photo: str) -> str | None:
    """Fill in a single photo page. Return the photo's directory URL, or
    None when the album has no such photo."""
    meta = data['meta']
    entries = cast(list[Entry], data['entries'])
    reverse_order = bool(meta['reverse_order'])

    photo_idx = _find_photo_index(entries, photo, reverse_order)
    if photo_idx is None:
        return None

    # position in the (possibly reversed) list and the step to the next photo
    if reverse_order:
        pos, step = len(entries) - photo_idx, -1
    else:
        pos, step = photo_idx - 1, 1

    meta['title'] = f'#{photo_idx} - {meta["title"] or links.album}'
    entry = data['entry'] = entries[pos]
    entry['alt'] = _entry_alt(entry)

    # determine canonical photo url
    canon_link = f'{photo_idx}/{entry["slug"]}' if 'slug' in entry else photo_idx
    data['canonical_url'] = reverse(
        'photo', kwargs={'album': links.album, 'photo': canon_link}
    )
    data['prev_entry'] = _nav_link(entries, pos - 1, photo_idx - step, links)
    data['next_entry'] = _nav_link(entries, pos + 1, photo_idx + step, links)

    path = _photo_media(entry, meta, links)

    entry['link'] = reverse('album', kwargs={'album': links.album})
    page = pos // int(meta['ppp']) + 1
    if page > 1:
        entry['link'] += page_url({}, links.album, '', page)

    meta['description'] = entry.get('description', meta['title'])
    meta['copyright'] = entry.get('copyright') or meta.get('copyright')
    meta['copyright_link'] = entry.get('copyright_link') or meta.get('copyright_link')

    data['wxpb_settings'] = _wxpb_settings(data, [entry])
    return path


def _find_photo_index(
    entries: list[Entry], photo: str, reverse_order: bool
) -> int | None:
    """The 1-based index of the photo addressed by number or by filename."""
    lentries = len(entries)
    number = photo.split('/')[0]
    if number.isdigit():
        photo_idx = int(number)
        return photo_idx if 1 <= photo_idx <= lentries else None

    if not photo.lower().endswith('.jpg'):
        photo += '.jpg'
    for pos, entry in enumerate(entries):
        if _entry_filename(entry) == photo:
            return lentries - pos if reverse_order else pos + 1
    return None


def _entry_filename(entry: Entry) -> str | None:
    """The image file, or the first video source, of an entry."""
    image = entry.get('image')
    if image:
        return image if isinstance(image, str) else image['file']
    video = entry.get('video')
    if isinstance(video, str):
        return video
    if isinstance(video, list) and video:
        first = video[0]
        return first if isinstance(first, str) else first['src']
    return None


def _nav_link(entries: list[Entry], pos: int, number: int, links: _Links) -> str | None:
    """Link to the photo at `pos`, shown as `number`; None past either end."""
    if not 0 <= pos < len(entries):
        return None
    slug = entries[pos].get('slug')
    return links.photo(f'{number}/{slug}' if slug else number)


def _photo_media(entry: Entry, meta: MetaData, links: _Links) -> str:
    """Set the photo's URL and size. Return its directory URL."""
    meta_path = meta.get('path', '')
    img = entry.get('image')
    size: tuple[int, int] | str | None
    if isinstance(img, str):
        f = img
        path = meta_path
        size = entry.get('size') or meta.get('default_image_size')
    elif img:
        f = img['file']
        path = img.get('path', meta_path)
        size = img.get('size') or meta.get('default_image_size')
    else:  # video
        _parse_video_entry(entry)
        path = meta_path
        f = size = ''

    path = links.media_dir(path)
    entry['url'] = urljoin(path, f)
    entry['size'] = size
    return path


def _album_context(data: Album, links: _Links, page: int, geomap: bool) -> str:
    """Fill in an album (or geomap) page. Return the directory URL of the
    last entry's thumbnail, which a relative cover is resolved against."""
    meta = data['meta']
    if geomap:
        meta['ppp'] = 500

    if meta.get('prev_story'):
        data['prev_story'] = _story_link(meta['prev_story'])
    if meta.get('next_story'):
        data['next_story'] = _story_link(meta['next_story'])

    entries_paginated = _paginate(cast(list[Entry], data['entries']), meta['ppp'], page)
    data['entries'] = entries_paginated

    path = urljoin(links.baseurl, meta.get('path', ''))
    for entry in entries_paginated.object_list:
        path = _album_entry(entry, meta, links)

    # grouping entries into columns
    columns = int(meta.get('columns', 3))
    if columns:
        data['groups'] = (
            (e for e in t if e is not None)
            for t in zip_longest(*(iter(entries_paginated.object_list),) * columns)
        )

    if geomap:
        data['wxpb_settings'] = _wxpb_settings(
            data, list(entries_paginated.object_list)
        )
        del data['entries']
    return path


def _story_link(story: str) -> str:
    return story if story.startswith('/') else reverse('album', kwargs={'album': story})


def _paginate(entries: list[Entry], ppp: int, page: int) -> Page[Entry]:
    """The requested page (the last one if it is out of range), with a
    `page_range_limited` of up to six pages either side on its paginator."""
    paginator = Paginator(entries, ppp)
    try:
        entries_paginated: Page[Entry] = paginator.page(page)
    except (EmptyPage, InvalidPage):
        entries_paginated = paginator.page(paginator.num_pages)

    pg_range = 6
    cindex = entries_paginated.number - 1
    page_range = range(1, paginator.num_pages + 1)
    cast(Any, paginator).page_range_limited = page_range[
        max(cindex - pg_range, 0) : cindex + pg_range
    ]
    return entries_paginated


def _album_entry(entry: Entry, meta: MetaData, links: _Links) -> str:
    """Set an album entry's full-size URL, thumbnail URL and size, and link.
    Return the thumbnail's directory URL."""
    entry['alt'] = _entry_alt(entry)
    meta_path = meta.get('path', '')
    img: str | Image | None = entry.get('image')
    if img:
        f = img if isinstance(img, str) else img['file']
        entry['url_full'] = urljoin(urljoin(links.baseurl, meta_path), f)

    if meta.get('thumbs_skip'):
        img = entry.get('image')
        path = meta_path
        item_type = 'image'
    else:
        img = entry.get('thumb', entry.get('image'))
        path = meta.get('path_thumb', meta_path)
        item_type = 'thumb'

    if not img:  # non-image entries
        _parse_video_entry(entry)
        return urljoin(links.baseurl, meta_path)

    size_key = f'default_{item_type}_size'
    if isinstance(img, str):
        f = img
        entry['size'] = cast(Any, meta).get(size_key)
    else:
        f = img['file']
        path = img.get('path', meta.get('path_thumb', meta_path))
        entry['size'] = img.get('size', cast(Any, meta).get(size_key))

    path = links.media_dir(path)
    entry['url'] = urljoin(path, f)
    if 'link' not in entry:
        entry['link'] = _album_entry_link(entry, links)
    return path


def _entry_alt(entry: Entry) -> str:
    """Text alternative for an entry's image: its own `alt`, title, comment
    or description, falling back to the photo number."""
    for key in ('alt', 'title', 'comment', 'description'):
        text = html.unescape(strip_tags(str(entry.get(key) or ''))).strip()
        if text:
            return Truncator(' '.join(text.split())).chars(125)
    return _('Photo %(number)s') % {'number': entry.get('index', '')}


def _album_entry_link(entry: Entry, links: _Links) -> str:
    if 'album' in entry:
        return reverse('album', kwargs={'album': entry['album']})
    slug = entry.get('slug')
    return links.photo(f'{entry["index"]}/{slug}' if slug else entry['index'])


def _wxpb_settings(data: Album, entries: list[Entry]) -> str:
    """Map plugin settings as JSON, with the entries grouped by GPS point."""
    geo_points_map: dict[tuple[float, float], list[Entry]] = {}
    for entry in entries:
        if 'geo' in entry:
            entry.pop('exif', None)
            geo_points_map.setdefault(entry['geo'], []).append(entry)
    geo_points = sorted(geo_points_map.items(), key=lambda x: x[1][0]['index'])

    wxpb_settings = dict(getattr(settings, 'WXPB_SETTINGS', None) or {})
    wxpb_settings.update(data.get('settings') or {})
    wxpb_settings['geo_points'] = geo_points
    return json.dumps(wxpb_settings)


def _cover_url(cover: str | None, path: str, site_url: str | None) -> str | None:
    if cover and not cover.startswith('/'):
        cover = urljoin(path, cover)
    if cover and site_url:
        cover = urljoin(site_url, cover)
    return cover


def _parse_video_entry(entry: Entry) -> None:
    video = entry.get('video')
    if video:
        if isinstance(video, str) and 'youtube.com/' in video:
            for v in re.findall(
                r'https?://(www\.)?youtube\.com/'
                r'watch\?v=([\-\w]+)(\S*)',
                video,
            ):
                entry['type'] = 'youtube'
                entry['vid'] = v[1]
        elif isinstance(video, str) and 'vimeo.com/' in video:
            for v in re.findall(r'https?://(www\.)?vimeo\.com/(\d+)', video):
                entry['type'] = 'vimeo'
                entry['vid'] = v[1]
        elif isinstance(video, str):
            entry['type'] = 'html5'
            entry['vid'] = [{'src': video, 'type': _get_mtype(video)}]
        elif isinstance(video, list):
            entry['type'] = 'html5'
            vid: list[VideoSrc] = []
            obj: VideoSrc | str
            for obj in video:
                if isinstance(obj, str):
                    vid.append({'src': obj, 'type': _get_mtype(obj)})
                else:
                    vid.append(obj)
            entry['vid'] = vid


_MIME_TYPES = {
    '.mp4': 'video/mp4',
    '.webm': 'video/webm',
    '.ogg': 'video/ogg',
    '.mov': 'video/quicktime',
}


def _get_mtype(video: str) -> str:
    for ext, mtype in _MIME_TYPES.items():
        if video.endswith(ext):
            return mtype
    return 'video'


def _albumfile_path(album_name: str) -> str:
    """The album's YAML file if it has one (and YAML is available), otherwise
    its JSON file. The file may not exist."""
    albumfile_yaml = os.path.join(settings.ALBUM_DIR, album_name + '.yaml')
    if yaml and os.path.isfile(albumfile_yaml):
        return albumfile_yaml
    return os.path.join(settings.ALBUM_DIR, album_name + '.json')


def _load_errors() -> tuple[type[Exception], ...]:
    if yaml:
        return (OSError, ValueError, yaml.YAMLError)
    return (OSError, ValueError)


def _open_albumfile(album_name: str) -> Album | None:
    albumfile = _albumfile_path(album_name)
    try:
        mtime = os.path.getmtime(albumfile)
    except OSError:
        logger.debug('album not found: %s', album_name)
        return None

    cache_key = 'album:' + album_name
    cache_data = cache.get(cache_key)
    if cache_data and 'data' in cache_data and cache_data.get('mtime', 0) >= mtime:
        logger.debug('cache: get %s (%s)', cache_key, mtime)
        return cast(Album, cache_data['data'])

    try:
        with open(albumfile, 'r', encoding='utf-8') as fp:
            if albumfile.endswith('.yaml'):
                data = cast(Album, yaml.load(fp.read(), Loader=YamlLoader))
            else:
                data = cast(Album, json.loads(fp.read()))
    except _load_errors() as exc:
        logger.error('cannot load album file %s: %s', albumfile, exc)
        return None

    logger.debug('cache: set %s (%s)', cache_key, mtime)
    cache.set(cache_key, {'mtime': mtime, 'data': data}, None)

    return data
