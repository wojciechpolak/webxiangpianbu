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

import re
import os
import json
from typing import Any, MutableMapping, cast

import math
import logging

from urllib.parse import urljoin
from itertools import zip_longest

from django.conf import settings
from django.urls import reverse
from django.core.cache import cache
from django.core.paginator import Page, Paginator, InvalidPage, EmptyPage
from .templatetags.page import page as page_url
from .typing import Album, Entry, VideoSrc

yaml: Any = None
YamlLoader: Any = None

try:
    import yaml as _yaml

    yaml = _yaml

    YamlLoader = cast(Any, getattr(_yaml, 'CLoader', _yaml.Loader))
except ImportError:
    yaml = None

logger = logging.getLogger('main')


def get_data(
    album: str,
    photo=None,
    page=1,
    site_url=None,
    is_mobile=False,
    staticgen=False,
    relative_links=False,
) -> Album | None:
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

    album_data = _open_albumfile(album)
    if not album_data:
        return None

    data['meta'].update(album_data.get('meta', {}))
    data['meta']['title_gallery'] = data['meta']['title'] or album
    data['entries'] = album_data.get('entries', [])

    # force mobile template
    if data['meta']['template'] == 'story' and is_mobile:
        data['meta']['template'] = 'floating'
        data['meta']['thumbs_skip'] = False

    baseurl = data['URL_PHOTOS']
    meta_path = data['meta'].get('path', '')

    # set a constant entry indexes
    entries = cast(list[Entry], data['entries'])

    for i, entry in enumerate(entries, start=1):
        entry['index'] = i

    reverse_order = bool(data['meta']['reverse_order'])
    if reverse_order:
        entries = list(reversed(entries))
        data['entries'] = entries

    if photo and photo != 'geomap':
        mode = 'photo'
        entries = cast(list[Entry], data['entries'])
        lentries = len(entries)

        photo_idx = photo.split('/')[0]
        if photo_idx.isdigit():
            photo_idx = int(photo_idx)
            if photo_idx < 1 or photo_idx > lentries:
                return None
        else:
            photo_idx = None
            if not photo.lower().endswith('.jpg'):
                photo += '.jpg'
            for idx, ent in enumerate(entries):
                if ent.get('image', None):
                    image = ent['image']
                    if isinstance(image, str):
                        f = image
                    else:
                        f = image['file']
                elif ent.get('video', None):
                    video = ent['video']
                    if isinstance(video, str):
                        f = video
                    elif isinstance(video, list):
                        first_video = video[0]
                        if isinstance(first_video, str):
                            f = first_video
                        else:
                            f = first_video['src']
                    else:
                        continue
                if photo == f:
                    if reverse_order:
                        photo_idx = lentries - idx
                    else:
                        photo_idx = idx + 1
                    break
            if photo_idx is None:
                return None

        if reverse_order:
            idx = lentries - photo_idx
            data['meta']['title'] = '#%s - %s' % (
                photo_idx,
                data['meta']['title'] or album,
            )
            prev_idx = photo_idx + 1 if photo_idx < lentries else None
            next_idx = photo_idx - 1 if photo_idx > 1 else None
        else:
            idx = photo_idx - 1
            data['meta']['title'] = '#%s - %s' % (
                photo_idx,
                data['meta']['title'] or album,
            )
            prev_idx = photo_idx - 1 if photo_idx > 1 else None
            next_idx = photo_idx + 1 if photo_idx < lentries else None

        entry = data['entry'] = entries[idx]

        # determine canonical photo url
        canon_link = (
            '%s/%s' % (photo_idx, entry['slug']) if 'slug' in entry else photo_idx
        )
        data['canonical_url'] = reverse(
            'photo', kwargs={'album': album, 'photo': canon_link}
        )

        if prev_idx is not None:
            if reverse_order:
                slug = entries[idx - 1].get('slug')
            else:
                slug = entries[prev_idx - 1].get('slug')
            prev_photo = '%s/%s' % (prev_idx, slug) if slug else prev_idx
            if relative_links:
                data['prev_entry'] = reverse(
                    'photo_relative', kwargs={'photo': prev_photo}
                ).replace('/', '')
            else:
                data['prev_entry'] = reverse(
                    'photo', kwargs={'album': album, 'photo': prev_photo}
                )
        else:
            data['prev_entry'] = None

        if next_idx is not None:
            if reverse_order:
                slug = entries[idx + 1].get('slug')
            else:
                slug = entries[next_idx - 1].get('slug')
            next_photo = '%s/%s' % (next_idx, slug) if slug else next_idx
            if relative_links:
                data['next_entry'] = reverse(
                    'photo_relative', kwargs={'photo': next_photo}
                ).replace('/', '')
            else:
                data['next_entry'] = reverse(
                    'photo', kwargs={'album': album, 'photo': next_photo}
                )
        else:
            data['next_entry'] = None

        img = entry.get('image')
        if isinstance(img, str):
            f = img
            path = meta_path
            size = entry.get('size') or data['meta'].get('default_image_size')
        elif img:
            f = img['file']
            path = img.get('path', meta_path)
            size = img.get('size') or data['meta'].get('default_image_size')
        else:  # video
            _parse_video_entry(entry)
            path = meta_path
            f = size = ''

        if staticgen:
            path = baseurl
        else:
            path = urljoin(baseurl, path)
        entry['url'] = urljoin(path, f)
        entry['size'] = size

        if reverse_order:
            page = int(
                math.floor((lentries - photo_idx) / float(data['meta']['ppp'])) + 1
            )
        else:
            page = int(math.ceil(photo_idx / float(data['meta']['ppp'])))

        entry['link'] = reverse('album', kwargs={'album': album})
        if relative_links:
            entry['link'] = 'index.html'

        if page > 1:
            entry['link'] += page_url({}, album, '', page)

        data['meta']['description'] = entry.get('description', data['meta']['title'])
        data['meta']['copyright'] = entry.get('copyright') or data['meta'].get(
            'copyright'
        )
        data['meta']['copyright_link'] = entry.get('copyright_link') or data[
            'meta'
        ].get('copyright_link')

        geo_points_map: dict[tuple[float, float], list[Entry]] = {}
        if 'geo' in entry:
            p = entry['geo']
            if p not in geo_points_map:
                geo_points_map[p] = []
            if 'exif' in entry:
                del entry['exif']
            geo_points_map[p].append(entry)
        geo_points = sorted(
            [(k, v) for k, v in list(geo_points_map.items())],
            key=lambda x: x[1][0]['index'],
        )
        wxpb_settings = getattr(settings, 'WXPB_SETTINGS', None) or {}
        wxpb_settings.update(data.get('settings') or {})
        wxpb_settings['geo_points'] = geo_points
        data['wxpb_settings'] = json.dumps(wxpb_settings)

    else:
        if photo == 'geomap':
            mode = 'geomap'
        else:
            mode = 'album'

        if mode == 'geomap':
            data['meta']['ppp'] = 500

        prev_story = data['meta'].get('prev_story')
        if prev_story:
            if prev_story.startswith('/'):
                data['prev_story'] = prev_story
            else:
                data['prev_story'] = reverse('album', kwargs={'album': prev_story})

        next_story = data['meta'].get('next_story')
        if next_story:
            if next_story.startswith('/'):
                data['next_story'] = next_story
            else:
                data['next_story'] = reverse('album', kwargs={'album': next_story})

        entries = cast(list[Entry], data['entries'])
        paginator = Paginator(entries, data['meta']['ppp'])
        try:
            entries_paginated: Page[Entry] = paginator.page(page)
        except (EmptyPage, InvalidPage):
            entries_paginated = paginator.page(paginator.num_pages)
            page = paginator.num_pages
        data['entries'] = entries_paginated

        # use a limited page range
        pg_range = 6
        x_page_range = paginator.page_range
        page_range = range(x_page_range[0], x_page_range[-1] + 1)
        cindex = page_range.index(page)
        cmin, cmax = cindex - pg_range, cindex + pg_range
        if cmin < 0:
            cmin = 0
        cast(Any, paginator).page_range_limited = page_range[cmin:cmax]

        for i, entry in enumerate(entries_paginated.object_list):
            img = entry.get('image')
            path = data['meta'].get('path', meta_path)
            path = urljoin(baseurl, path)
            if isinstance(img, str):
                entry['url_full'] = urljoin(path, img)
            elif img:
                entry['url_full'] = urljoin(path, img['file'])

            if data['meta'].get('thumbs_skip'):
                img = entry.get('image')
                path = data['meta'].get('path', meta_path)
                item_type = 'image'
            else:
                img = entry.get('thumb', entry.get('image'))
                path = data['meta'].get('path_thumb', meta_path)
                item_type = 'thumb'

            if img:
                size_key: str = 'default_%s_size' % item_type
                if isinstance(img, str):
                    f = img
                    entry['size'] = data['meta'].get(size_key)
                else:
                    f = img['file']
                    path = img.get('path', data['meta'].get('path_thumb', meta_path))
                    entry['size'] = img.get('size', data['meta'].get(size_key))

                if staticgen:
                    path = baseurl
                else:
                    path = urljoin(baseurl, path)
                entry['url'] = urljoin(path, f)

                if 'link' in entry:
                    pass
                elif 'album' in entry:
                    entry['link'] = reverse('album', kwargs={'album': entry['album']})
                else:
                    slug = entry.get('slug')
                    link = '%s/%s' % (entry['index'], slug) if slug else entry['index']
                    if relative_links:
                        entry['link'] = reverse(
                            'photo_relative', kwargs={'photo': link}
                        ).replace('/', '')
                    else:
                        entry['link'] = reverse(
                            'photo', kwargs={'album': album, 'photo': link}
                        )

            else:  # non-image entries
                path = urljoin(baseurl, meta_path)
                _parse_video_entry(entry)

        # grouping entries into columns
        columns = int(data['meta'].get('columns', 3))
        if columns:
            data['groups'] = (
                (e for e in t if e is not None)
                for t in zip_longest(*(iter(entries_paginated.object_list),) * columns)
            )

        # set up geo points
        if mode == 'geomap':
            geomap_points_map: dict[tuple[float, float], list[Entry]] = {}
            for entry in entries_paginated.object_list:
                if 'geo' in entry:
                    p = entry['geo']
                    if p not in geomap_points_map:
                        geomap_points_map[p] = []
                    if 'exif' in entry:
                        del entry['exif']
                    geomap_points_map[p].append(entry)
            geo_points = sorted(
                [(k, v) for k, v in list(geomap_points_map.items())],
                key=lambda x: x[1][0]['index'],
            )
            wxpb_settings = getattr(settings, 'WXPB_SETTINGS', None) or {}
            wxpb_settings.update(data.get('settings') or {})
            wxpb_settings['geo_points'] = geo_points
            data['wxpb_settings'] = json.dumps(wxpb_settings)
            del data['entries']

    if data['meta']['style'] and not data['meta']['style'].endswith('.css'):
        data['meta']['style'] += '.css'

    # handle cover's URL
    cover = data['meta']['cover']
    if cover and not cover.startswith('/'):
        cover = urljoin(path, cover)
    if cover and site_url:
        cover = urljoin(site_url, cover)
    data['meta']['cover'] = cover

    ctx: Album = {
        'mode': mode,
        'album': album,
    }
    ctx.update(data)

    return ctx


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


def _get_mtype(video: str) -> str:
    mtype = 'video'
    if video.endswith('.mp4'):
        mtype = 'video/mp4'
    elif video.endswith('.webm'):
        mtype = 'video/webm'
    elif video.endswith('.ogg'):
        mtype = 'video/ogg'
    elif video.endswith('.mov'):
        mtype = 'video/quicktime'
    return mtype


def _open_albumfile(album_name: str) -> Album | None:
    albumfile_yaml = os.path.join(settings.ALBUM_DIR, album_name + '.yaml')
    albumfile_json = os.path.join(settings.ALBUM_DIR, album_name + '.json')

    cache_key = 'album:' + album_name
    cache_data = cache.get(cache_key)

    try:
        mt1 = os.path.getmtime(albumfile_yaml)
    except Exception:
        try:
            mt1 = os.path.getmtime(albumfile_json)
        except Exception as exc:
            print('_open_albumfile exception', exc)
            return None
    try:
        mt2 = cache_data['mtime']
    except Exception:
        mt2 = 0

    if cache_data and 'data' in cache_data and mt2 >= mt1:
        logger.debug('cache: get %s (%s)', cache_key, mt1)
        return cast(Album, cache_data['data'])

    if os.path.isfile(albumfile_yaml) and yaml:
        try:
            with open(albumfile_yaml, 'r', encoding='utf-8') as fp:
                data = cast(Album, yaml.load(fp.read(), Loader=YamlLoader))
        except Exception as e:
            raise e
    elif os.path.isfile(albumfile_json):
        try:
            with open(albumfile_json, 'r', encoding='utf-8') as fp:
                data = cast(Album, json.loads(fp.read()))
        except Exception as e:
            raise e
    else:
        return None

    # save cache
    logger.debug('cache: set %s (%s)', cache_key, mt1)
    cache.set(cache_key, {'mtime': mt1, 'data': data}, None)

    return data
