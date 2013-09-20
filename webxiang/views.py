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

import re
import os
import math
import itertools
import urlparse
import marshal
import py_compile

from django.conf import settings
from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import render
from django.template import TemplateDoesNotExist
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, InvalidPage, EmptyPage

try:
    import yaml
except ImportError:
    yaml = None

try:
    import simplejson as json
except ImportError:
    import json


def display(request, album='index', photo=None):
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    data = {
        'URL_PHOTOS': settings.WEBXIANG_PHOTOS_URL,
        'LAZY_LOADING': settings.WEBXIANG_PHOTOS_LAZY,
        'meta': {
            'template': 'default.html',
            'style': 'base.css',
            'title': 'Albums',
            'robots': 'noindex,nofollow',
            'custom_menu': False,
            'columns': 3,
            'ppp': 36,
            'reverse-order': False,
            'default-thumb-size': (180, 180),
            'cover': None,
        },
        'entries': [],
    }

    jdata = _open_albumfile(album)
    data['meta'].update(jdata.get('meta', {}))
    data['meta']['title_gallery'] = data['meta']['title'] or album
    data['entries'] = jdata.get('entries', [])

    baseurl = data['URL_PHOTOS']
    meta_path = data['meta'].get('path', '')

    # force mobile template
    if data['meta']['template'] == 'story' and (
        'Mobi' in request.META.get('HTTP_USER_AGENT', '') or
            request.GET.get('mobile')):
        data['meta']['template'] = 'floating'
        data['meta']['thumbs-skip'] = False

    # set a constant entry indexes
    for i, entry in enumerate(data['entries'], start=1):
        entry['index'] = i

    reverse_order = bool(data['meta']['reverse-order'])
    if reverse_order:
        data['entries'] = list(reversed(data['entries']))

    if photo:
        mode = 'photo'
        lentries = len(data['entries'])

        photo_idx = photo.split('/')[0]
        if photo_idx.isdigit():
            photo_idx = int(photo_idx)
        else:
            photo_idx = None
            if not photo.lower().endswith('.jpg'):
                photo += '.jpg'
            for idx, ent in enumerate(data['entries']):
                if isinstance(ent['image'], basestring):
                    f = ent['image']
                else:
                    f = ent['image']['file']
                if photo == f:
                    if reverse_order:
                        photo_idx = lentries - idx
                    else:
                        photo_idx = idx + 1
                    break
            if photo_idx is None:
                raise Http404

        if reverse_order:
            idx = lentries - photo_idx
            data['meta']['title'] = '#%s - %s' % \
                (photo_idx, data['meta']['title'] or album)
            prev_idx = photo_idx + 1 if photo_idx < lentries else None
            next_idx = photo_idx - 1 if photo_idx > 1 else None
        else:
            idx = photo_idx - 1
            data['meta']['title'] = '#%s - %s' % \
                (photo_idx, data['meta']['title'] or album)
            prev_idx = photo_idx - 1 if photo_idx > 1 else None
            next_idx = photo_idx + 1 if photo_idx < lentries else None

        entry = data['entry'] = data['entries'][idx]

        # determine canonical photo url
        canon_link = '%s/%s' % (photo_idx, entry['slug']) \
            if 'slug' in entry else photo_idx
        canonical_url = reverse('photo', kwargs={
                'album': album,
                'photo': canon_link})
        if canonical_url != request.path:
            return HttpResponsePermanentRedirect(canonical_url)

        if prev_idx is not None:
            if reverse_order:
                slug = data['entries'][idx - 1].get('slug')
            else:
                slug = data['entries'][prev_idx - 1].get('slug')
            prev_photo = '%s/%s' % (prev_idx, slug) if slug else prev_idx
            data['prev_entry'] = reverse('photo', kwargs={
                    'album': album,
                    'photo': prev_photo})
        else:
            data['prev_entry'] = None

        if next_idx is not None:
            if reverse_order:
                slug = data['entries'][idx + 1].get('slug')
            else:
                slug = data['entries'][next_idx - 1].get('slug')
            next_photo = '%s/%s' % (next_idx, slug) if slug else next_idx
            data['next_entry'] = reverse('photo', kwargs={
                    'album': album,
                    'photo': next_photo})
        else:
            data['next_entry'] = None

        img = entry.get('image')
        if isinstance(img, basestring):
            f = entry['image']
            path = meta_path
            size = entry.get('size') or data[
                'meta'].get('default-image-size')
        elif img:
            f = entry['image']['file']
            path = entry['image'].get('path', meta_path)
            size = entry['image'].get('size') or data[
                'meta'].get('default-image-size')
        else:  # video
            _parse_video_entry(entry)
            path = meta_path
            f = size = ''

        path = urlparse.urljoin(baseurl, path)
        entry['url'] = urlparse.urljoin(path, f)
        entry['size'] = size

        if reverse_order:
            page = int(math.floor((lentries - photo_idx) /
                                  float(data['meta']['ppp'])) + 1)
        else:
            page = int(math.ceil(photo_idx / float(data['meta']['ppp'])))

        entry['link'] = reverse('album', kwargs={'album': album})
        if page > 1:
            entry['link'] += '?page=%s' % page

        data['meta']['description'] = entry.get('description',
                                                data['meta']['title'])
        data['meta']['copyright'] = entry.get('copyright',
                                              data['meta'].get('copyright'))

    else:
        mode = 'album'

        paginator = Paginator(data['entries'], data['meta']['ppp'])
        try:
            data['entries'] = paginator.page(page)
        except (EmptyPage, InvalidPage):
            data['entries'] = paginator.page(paginator.num_pages)
            page = paginator.num_pages

        # use a limited page range
        pg_range = 6
        cindex = paginator.page_range.index(page)
        cmin, cmax = cindex - pg_range, cindex + pg_range
        if cmin < 0:
            cmin = 0
        paginator.page_range_limited = paginator.page_range[cmin:cmax]

        for i, entry in enumerate(data['entries'].object_list):
            if data['meta'].get('thumbs-skip'):
                img = entry.get('image')
                path = data['meta'].get('path', meta_path)
                item_type = 'image'
            else:
                img = entry.get('thumb', entry.get('image'))
                path = data['meta'].get('path-thumb', meta_path)
                item_type = 'thumb'

            if img:
                if isinstance(img, basestring):
                    f = img
                    entry['size'] = data['meta'].get('default-%s-size' %
                                                     item_type)
                else:
                    f = img['file']
                    path = img.get('path',
                                   data['meta'].get('path-thumb', meta_path))
                    entry['size'] = img.get(
                        'size',
                        data['meta'].get('default-%s-size' % item_type))

                path = urlparse.urljoin(baseurl, path)
                entry['url'] = urlparse.urljoin(path, f)

                if 'image' in entry:
                    entry['url_full'] = urlparse.urljoin(path, f)

                if 'link' in entry:
                    pass
                elif 'album' in entry:
                    entry['link'] = reverse('album', kwargs={
                        'album': entry['album']})
                else:
                    slug = entry.get('slug')
                    link = '%s/%s' % (entry['index'], slug) \
                        if slug else entry['index']
                    entry['link'] = reverse('photo', kwargs={
                            'album': album,
                            'photo': link})

            else:  # non-image entries
                path = urlparse.urljoin(baseurl, meta_path)
                _parse_video_entry(entry)


        # grouping entries into columns
        columns = int(data['meta'].get('columns', 3))
        if columns:
            data['groups'] = (
                (e for e in t if e != None)
                for t in itertools.izip_longest(
                    *(iter(data['entries'].object_list),) * columns)
            )

    if data['meta']['style'] and not data['meta']['style'].endswith('.css'):
        data['meta']['style'] += '.css'

    if data['meta']['cover'] and not data['meta']['cover'].startswith('/'):
        data['meta']['cover'] = urlparse.urljoin(path, data['meta']['cover'])

    ctx = {
        'mode': mode,
        'album': album,
    }
    ctx.update(data)

    tpl = data['meta'].get('template', 'default.html')
    if not tpl.endswith('.html'):
        tpl += '.html'

    try:
        return render(request, tpl, ctx)
    except TemplateDoesNotExist:
        return render(request, 'default.html', ctx)


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


def _parse_video_entry(entry):
    video = entry.get('video')
    if video:
        if 'youtube.com/' in video:
            for v in re.findall(r'https?://(www\.)?youtube\.com/'
                                'watch\?v=([\-\w]+)(\S*)', video):
                entry['type'] = 'youtube'
                entry['vid'] = v[1]
        elif 'vimeo.com/' in video:
            for v in re.findall(
                    r'https?://(www\.)?vimeo\.com/(\d+)', video):
                entry['type'] = 'vimeo'
                entry['vid'] = v[1]


def _open_albumfile(album_name):
    albumfile_yaml = os.path.join(settings.ALBUM_DIR, album_name + '.yaml')
    albumfile_json = os.path.join(settings.ALBUM_DIR, album_name + '.json')
    cachefile = os.path.join(settings.CACHE_DIR, album_name + '.py')

    try:
        mt1 = os.path.getmtime(albumfile_yaml)
    except:
        try:
            mt1 = os.path.getmtime(albumfile_json)
        except:
            raise Http404
    try:
        mt2 = os.path.getmtime(cachefile + 'c')
    except:
        mt2 = 0

    loc = {}
    try:
        fp = open(cachefile + 'c', 'rb')
        pcd = fp.read()
        fp.close()
        code = marshal.loads(pcd[8:])
        exec code in {}, loc
    except:
        pass

    if mt2 > mt1 and 'cache' in loc:
        data = loc['cache']
        return data

    if os.path.isfile(albumfile_yaml) and yaml:
        try:
            album_content = open(albumfile_yaml, 'r').read()
            data = yaml.load(album_content)
        except Exception, e:
            raise e
    elif os.path.isfile(albumfile_json):
        try:
            album_content = open(albumfile_json, 'r').read()
            data = json.loads(album_content)
        except Exception, e:
            raise e
    else:
        raise Http404

    # save cache file
    fp = open(cachefile, 'w')
    fp.write('cache=' + str(data))
    fp.close()
    py_compile.compile(cachefile)
    os.unlink(cachefile)

    return data
