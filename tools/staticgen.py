#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
"""
#  WebXiangpianbu Copyright (C) 2014, 2015, 2023 Wojciech Polak
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

import os
import sys
import json
import getopt
import shutil
import signal
import codecs
from datetime import datetime
from urllib.parse import urljoin

import http.server
import socketserver

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'webxiang.settings'
sys.path.insert(0, os.path.join(SITE_ROOT, '../'))

import django
if hasattr(django, 'setup'):
    django.setup()

from django.conf import settings

try:
    from django.shortcuts import render
except ImportError as exc:
    print(exc)
    print("Copy `webxiang/settings_sample.py` to " \
          "`webxiang/settings.py` and modify it to your needs.")
    sys.exit(1)

from django.urls import set_urlconf, set_script_prefix
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.translation import gettext as _
from webxiang import webxiang

__generated = set()
__items_no = 0


def main():
    opts = {
        'verbose': 1,
        'output_dir': None,
        'album_dir_in': getattr(settings, 'ALBUM_DIR', 'albums'),
        'photo_dir_in': getattr(settings, 'WEBXIANG_PHOTOS_ROOT', ''),
        'root': '/',
        'assets_url': getattr(settings, 'STATIC_URL', 'assets/'),
        'photos_url': getattr(settings, 'WEBXIANG_PHOTOS_URL', 'data/'),
        'relative_links': False,
        'names': 'index',
        'lang': 'en',
        'quick': False,
        'copy': False,
        'serve': None,
        'port': 8000,
    }

    try:
        gopts, args = getopt.getopt(sys.argv[1:], 'v:yl:sp:',
                                    ['help',
                                     'verbose=',
                                     'lang=',
                                     'output-dir=',
                                     'album-dir=',
                                     'photo-dir=',
                                     'root=',
                                     'assets-url=',
                                     'photos-url=',
                                     'relative-links',
                                     'copy',
                                     'quick=',
                                     'serve=',
                                     'port=',
                                     ])
        for o, arg in gopts:
            if o == '--help':
                raise getopt.GetoptError('')
            if o in ('-v', '--verbose'):
                opts['verbose'] = int(arg)
            elif o == '--output-dir':
                opts['output_dir'] = arg
            elif o == '--album-dir':
                opts['album_dir_in'] = arg
                settings.ALBUM_DIR = opts['album_dir_in']
            elif o == '--photo-dir':
                opts['photo_dir_in'] = arg
            elif o == '--relative-links':
                opts['relative_links'] = True
                opts['root'] = ''
            elif o == '--root':
                if arg and not arg.endswith('/'):
                    arg += '/'
                opts['root'] = arg
            elif o == '--assets-url':
                if not arg.endswith('/'):
                    arg += '/'
                opts['assets_url'] = arg
            elif o == '--photos-url':
                if not arg.endswith('/'):
                    arg += '/'
                opts['photos_url'] = arg
            elif o in ('-l', '--lang'):
                opts['lang'] = arg
            elif o == '--copy':
                opts['copy'] = True
            elif o in ('-s', '--serve'):
                opts['serve'] = arg
            elif o in ('-p', '--port'):
                opts['port'] = int(arg)
            elif o == '--quick':  # a quick shortcut
                arg = os.path.expanduser(arg).rstrip('/')
                opts['quick'] = arg
                args = [os.path.basename(arg)]

        if len(args):
            opts['names'] = args[0]
            if len(args) > 1:
                opts['output_dir'] = args[1]
        else:
            opts['names'] = 'index'

    except getopt.GetoptError:
        print("Usage: %s [OPTION...] [ALBUM-NAME1,NAME2]" % sys.argv[0])
        print("%s -- album static HTML generator" % sys.argv[0])
        opts['output_dir_help'] = opts['output_dir'] or 'output-DATETIME/'
        print("""
 Options               Default values
 -v, --verbose         [%(verbose)s]
     --output-dir      [%(output_dir_help)s]
     --album-dir       [%(album_dir_in)s]
     --photo-dir       [%(photo_dir_in)s]
     --root            [%(root)s]
     --assets-url      [%(assets_url)s]
     --photos-url      [%(photos_url)s]
     --relative-links  [%(relative_links)s]
 -l, --lang            [%(lang)s]
     --copy            [%(copy)s]
     --quick           [folder's name]
 -s, --serve           [output dir]
 -p, --port            [%(port)s]
""" % opts)
        sys.exit(1)

    signal.signal(signal.SIGTERM, lambda signum, frame: __quit_app())
    signal.signal(signal.SIGINT, lambda signum, frame: __quit_app())

    if opts['serve']:
        serve(opts, opts['serve'])
        sys.exit(0)

    if opts['lang']:
        if opts['verbose'] > 1:
            print('Switching language to %s' % opts['lang'])
        translation.activate(opts['lang'])

    set_urlconf('webxiang.urls_static')
    set_script_prefix(opts['root'])

    root_dir = opts['output_dir'] and \
               os.path.expanduser(opts['output_dir']) or \
               'output-%s' % datetime.now().strftime('%Y%m%d-%H%M%S')

    output_dir = os.path.join(root_dir, opts['root'].lstrip('/'))

    if opts['quick']:
        cwd = os.getcwd()
        arg = opts['quick']
        arg_basename = os.path.basename(arg)
        opts['assets_dir'] = 'assets/'
        opts['assets_url'] = opts['assets_dir']
        opts['photo_dir_out'] = os.path.join(arg_basename, 'data/')
        if opts['relative_links']:
            opts['photos_url'] = 'data/'
        else:
            opts['photos_url'] = opts['photo_dir_out']
        opts['album_dir_in'] = os.path.relpath(arg, cwd) + '/'
        opts['photo_dir_in'] = opts['album_dir_in']
        settings.ALBUM_DIR = opts['album_dir_in']

    if not opts['relative_links']:
        opts['assets_url'] = urljoin(opts['root'], opts['assets_url'])
        opts['photos_url'] = urljoin(opts['root'], opts['photos_url'])

    settings.WEBXIANG_PHOTOS_URL = opts['photos_url']

    if opts['verbose'] > 1:
        print('WEBXIANG_PHOTOS_URL', settings.WEBXIANG_PHOTOS_URL)
        print('OPTIONS', json.dumps(opts, indent=2, sort_keys=True))

    try:
        if not os.path.exists(output_dir):
            print('Creating directory "%s"' % output_dir)
            os.makedirs(output_dir)
    except Exception:
        pass

    if not opts['photos_url'].startswith('http'):
        photo_dir_out = os.path.join(output_dir, opts['photo_dir_out'])

        if opts['copy']:
            print('Copying photos "%s" into "%s"' % \
                  (opts['photo_dir_in'].rstrip('/'), photo_dir_out))
            try:
                if not os.path.exists(photo_dir_out):
                    os.makedirs(photo_dir_out)
                __copytree(opts['photo_dir_in'].rstrip('/'), photo_dir_out)
            except Exception as exc:
                print('Copying photos', exc)

        else:
            print('Linking photos: ln -s %s %s' % \
                  (opts['photo_dir_in'].rstrip('/'), photo_dir_out.rstrip('/')))
            try:
                d = os.path.dirname(photo_dir_out.rstrip('/'))
                if not os.path.exists(d):
                    os.makedirs(d)
                os.symlink(opts['photo_dir_in'].rstrip('/'),
                           photo_dir_out.rstrip('/'))
            except Exception as exc:
                print('Linking photos', exc)

    print('Copying assets (JS, CSS, etc.) into "%s"' % \
        os.path.join(root_dir, opts['assets_dir'].lstrip('/')))
    try:
        __copytree(settings.STATIC_ROOT,
                   os.path.join(root_dir,
                                opts['assets_dir'].lstrip('/')))
    except Exception as exc:
        print('Copying assets', exc)

    print('Generating static pages.')
    for album_name in opts['names'].split(','):
        __gen_html_album(opts, album_name, output_dir=output_dir)

    if opts['verbose'] > 0:
        print()
    print('Finished %s' % output_dir)
    print('Done. Created %d files.' % __items_no)

    if opts['serve'] is not False:
        serve(opts, root_dir)


def __quit_app(code=0):
    print()
    sys.exit(code)


def serve(opts, root_dir=None):
    class SimpleServer(socketserver.TCPServer):
        allow_reuse_address = True

    if root_dir:
        os.chdir(root_dir)

    httpd = SimpleServer(('localhost', opts['port']),
                         http.server.SimpleHTTPRequestHandler)
    print('Serving at %s%s' % ('localhost:%d' % opts['port'], opts['root']))
    print('Quit the server with CONTROL-C.')
    httpd.serve_forever()


def __gen_html_album(opts, album_name: str, output_dir='.', page=1):
    global __generated, __items_no

    entry_id = '%s:%s' % (album_name, page)
    if entry_id in __generated:
        return
    __generated.add(entry_id)

    if page == 1:
        print(album_name, end=' ')

    data = webxiang.get_data(album=album_name, page=page,
                             staticgen=True,
                             relative_links=opts['relative_links'])
    if not data:
        return

    tpl = data['meta'].get('template') or 'default.html'
    if not tpl.endswith('.html'):
        tpl += '.html'

    settings.STATIC_URL = opts['assets_url']

    try:
        html = render_to_string(tpl, data)
    except TemplateDoesNotExist:
        html = render_to_string('default.html', data)

    if opts['relative_links']:
        html = html.replace('/' + opts['assets_url'], '../' + opts['assets_url'])

    if page > 1:
        output_file = os.path.join(output_dir, album_name,
                                   _('page-%(number)s.html') % {'number': page})
    else:
        output_file = os.path.join(output_dir, album_name, 'index.html')

    if opts['verbose'] > 1:
        print('writing %s' % output_file)
    elif opts['verbose'] == 1:
        sys.stdout.write('.')
        sys.stdout.flush()

    if not os.path.exists(os.path.dirname(output_file)):
        os.makedirs(os.path.dirname(output_file))

    f = codecs.open(output_file, 'w', 'utf-8')
    f.write(html)
    f.close()
    __items_no += 1

    # symlink '/index.html' to '/index/index.html'
    if album_name == 'index':
        os.symlink('index/index.html',
                   os.path.join(output_dir, 'index.html'))

    for i in data['entries'].paginator.page_range_limited:
        __gen_html_album(opts, album_name, output_dir=output_dir, page=i)

    for entry in data['entries']:
        if 'album' in entry:
            __gen_html_album(opts, entry['album'], output_dir)
        else:
            __gen_html_photo(opts, album_name,
                             '%s/' % entry['index'], output_dir)


def __gen_html_photo(opts, album_name: str, entry_idx: int, output_dir='.'):
    global __generated, __items_no

    entry_id = '%s/%s' % (album_name, entry_idx)
    if entry_id in __generated:
        return
    __generated.add(entry_id)

    photo_idx = entry_idx.split('/')[0]

    data = webxiang.get_data(album=album_name, photo=entry_idx,
                             staticgen=True,
                             relative_links=opts['relative_links'])
    if not data:
        return

    tpl = data['meta'].get('template') or 'default.html'
    if not tpl.endswith('.html'):
        tpl += '.html'

    settings.STATIC_URL = opts['assets_url']

    try:
        html = render_to_string(tpl, data)
    except TemplateDoesNotExist:
        html = render_to_string('default.html', data)

    if opts['relative_links']:
        html = html.replace('/' + opts['assets_url'], '../' + opts['assets_url'])

    os.makedirs(os.path.join(output_dir, album_name), exist_ok=True)

    entry = data['entries'][int(photo_idx) - 1]
    if 'slug' in entry:
        photo_name = '%s/%s.html' % (photo_idx, entry['slug'])
    else:
        photo_name = '%s.html' % photo_idx

    output_file = os.path.join(output_dir, album_name, photo_name)

    if not os.path.exists(os.path.dirname(output_file)):
        os.makedirs(os.path.dirname(output_file))

    if opts['verbose'] > 2:
        print('writing %s' % output_file)
    elif opts['verbose'] >= 1:
        sys.stdout.write('.')
        sys.stdout.flush()

    f = codecs.open(output_file, 'w', 'utf-8')
    f.write(html)
    f.close()
    __items_no += 1


def __copytree(src: str, dst: str, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)


if __name__ == '__main__':
    main()
