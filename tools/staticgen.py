#!/usr/bin/env python3
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

import argparse
import contextlib
import http.server
import json
import logging
import os
import shutil
import signal
import socketserver
import sys
from datetime import datetime
from typing import Any, NoReturn, cast
from urllib.parse import urljoin

import django
from django.conf import settings
from django.core.paginator import Page
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.urls import set_script_prefix, set_urlconf
from django.utils import translation
from django.utils.translation import gettext as _

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'webxiang.settings'
sys.path.insert(0, os.path.join(SITE_ROOT, '../'))
if hasattr(django, 'setup'):
    django.setup()
from webxiang import webxiang
from webxiang.typing import Album, Entry

logger = logging.getLogger('tools.staticgen')


def default_opts() -> dict[str, Any]:
    return {
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


def _with_slash(arg: str) -> str:
    return arg if arg.endswith('/') else arg + '/'


def _root(arg: str) -> str:
    return arg and _with_slash(arg)


def _quick(arg: str) -> str:
    return os.path.expanduser(arg).rstrip('/')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Render albums to static HTML, then serve the result.'
    )
    parser.add_argument(
        'names',
        nargs='?',
        metavar='ALBUM-NAME1,NAME2',
        help='albums to start from, default: %(default)s',
    )
    parser.add_argument(
        'output', nargs='?', metavar='OUTPUT-DIR', help='same as --output-dir'
    )
    parser.add_argument(
        '-v',
        '--verbose',
        type=int,
        metavar='LEVEL',
        help='0 quiet, 1 progress dots, 2 album pages, 3 every page; '
        'default: %(default)s',
    )
    parser.add_argument('--output-dir', metavar='DIR', help='default: output-DATETIME/')
    parser.add_argument(
        '--album-dir', dest='album_dir_in', metavar='DIR', help='default: %(default)s'
    )
    parser.add_argument(
        '--photo-dir', dest='photo_dir_in', metavar='DIR', help='default: %(default)s'
    )
    parser.add_argument(
        '--root', type=_root, metavar='PATH', help='default: %(default)s'
    )
    parser.add_argument(
        '--assets-url', type=_with_slash, metavar='URL', help='default: %(default)s'
    )
    parser.add_argument(
        '--photos-url', type=_with_slash, metavar='URL', help='default: %(default)s'
    )
    parser.add_argument(
        '--relative-links',
        action='store_true',
        help='link pages relative to each other; implies --root=',
    )
    parser.add_argument('-l', '--lang', help='default: %(default)s')
    parser.add_argument(
        '--copy', action='store_true', help='copy photos instead of symlinking them'
    )
    parser.add_argument(
        '--quick',
        type=_quick,
        metavar='DIR',
        help='render a folder holding both album files and photos, '
        'starting from the album named after the folder',
    )
    parser.add_argument(
        '-s', '--serve', metavar='DIR', help='only serve DIR, generate nothing'
    )
    parser.add_argument(
        '-p', '--port', type=int, metavar='N', help='default: %(default)s'
    )
    parser.set_defaults(**default_opts())
    return parser


def parse_args(argv: list[str]) -> dict[str, Any]:
    opts = vars(build_parser().parse_args(argv))
    output = opts.pop('output')
    if opts['relative_links']:
        opts['root'] = ''
    if opts['quick']:
        opts['names'] = os.path.basename(opts['quick'])
    elif output:
        opts['output_dir'] = output
    return opts


def main(argv: list[str] | None = None) -> None:
    opts = parse_args(sys.argv[1:] if argv is None else argv)

    signal.signal(signal.SIGTERM, lambda signum, frame: _quit_app())
    signal.signal(signal.SIGINT, lambda signum, frame: _quit_app())

    if opts['serve']:
        serve(opts, opts['serve'])
        sys.exit(0)

    if opts['lang']:
        if opts['verbose'] > 1:
            print(f'Switching language to {opts["lang"]}')
        translation.activate(opts['lang'])

    set_urlconf('webxiang.urls_static')
    set_script_prefix(opts['root'])

    root_dir = (
        opts['output_dir']
        and os.path.expanduser(opts['output_dir'])
        or f'output-{datetime.now().astimezone():%Y%m%d-%H%M%S}'
    )
    output_dir = os.path.join(root_dir, opts['root'].lstrip('/'))

    configure_urls(opts)

    if opts['verbose'] > 1:
        print('WEBXIANG_PHOTOS_URL', settings.WEBXIANG_PHOTOS_URL)
        print('OPTIONS', json.dumps(opts, indent=2, sort_keys=True))

    if not os.path.exists(output_dir):
        print(f'Creating directory "{output_dir}"')
        with contextlib.suppress(OSError):
            os.makedirs(output_dir)

    if not opts['photos_url'].startswith('http'):
        publish_photos(opts, os.path.join(output_dir, opts['photo_dir_out']))
    copy_assets(os.path.join(root_dir, opts['assets_dir'].lstrip('/')))

    print('Generating static pages.')
    generator = SiteGenerator(opts, output_dir)
    for album_name in opts['names'].split(','):
        generator.album(album_name)

    if opts['verbose'] > 0:
        print()
    print(f'Finished {output_dir}')
    print(f'Done. Created {generator.items_no:d} files.')

    serve(opts, root_dir)


def configure_urls(opts: dict[str, Any]) -> None:
    """Work out where assets and photos go and the URLs pages use for them."""
    if opts['quick']:
        arg = opts['quick']
        opts['assets_dir'] = 'assets/'
        opts['assets_url'] = opts['assets_dir']
        opts['photo_dir_out'] = os.path.join(os.path.basename(arg), 'data/')
        if opts['relative_links']:
            opts['photos_url'] = 'data/'
        else:
            opts['photos_url'] = opts['photo_dir_out']
        opts['album_dir_in'] = os.path.relpath(arg, os.getcwd()) + '/'
        opts['photo_dir_in'] = opts['album_dir_in']

    if not opts['relative_links']:
        opts['assets_url'] = urljoin(opts['root'], opts['assets_url'])
        opts['photos_url'] = urljoin(opts['root'], opts['photos_url'])

    settings.ALBUM_DIR = opts['album_dir_in']
    settings.WEBXIANG_PHOTOS_URL = opts['photos_url']


def publish_photos(opts: dict[str, Any], photo_dir_out: str) -> None:
    """Copy (--copy) or symlink the photo directory into the output."""
    photo_dir_in = opts['photo_dir_in'].rstrip('/')
    if opts['copy']:
        print(f'Copying photos "{photo_dir_in}" into "{photo_dir_out}"')
        try:
            os.makedirs(photo_dir_out, exist_ok=True)
            _copytree(photo_dir_in, photo_dir_out)
        except OSError as exc:
            logger.error('cannot copy photos: %s', exc)
    else:
        link = photo_dir_out.rstrip('/')
        print(f'Linking photos: ln -s {photo_dir_in} {link}')
        try:
            os.makedirs(os.path.dirname(link), exist_ok=True)
            os.symlink(photo_dir_in, link)
        except OSError as exc:
            logger.error('cannot link photos: %s', exc)


def copy_assets(assets_dir: str) -> None:
    print(f'Copying assets (JS, CSS, etc.) into "{assets_dir}"')
    try:
        _copytree(settings.STATIC_ROOT, assets_dir)
    except OSError as exc:
        logger.error('cannot copy assets: %s', exc)


def _quit_app(code: int = 0) -> NoReturn:
    print()
    sys.exit(code)


def serve(opts: dict[str, Any], root_dir: str | None = None) -> None:
    class SimpleServer(socketserver.TCPServer):
        allow_reuse_address = True

    if root_dir:
        os.chdir(root_dir)

    httpd = SimpleServer(
        ('localhost', opts['port']), http.server.SimpleHTTPRequestHandler
    )
    print(f'Serving at localhost:{opts["port"]:d}{opts["root"]}')
    print('Quit the server with CONTROL-C.')
    httpd.serve_forever()


class SiteGenerator:
    """Renders albums and their photos into `output_dir`, each page once."""

    def __init__(self, opts: dict[str, Any], output_dir: str = '.'):
        self.opts = opts
        self.output_dir = output_dir
        self.generated: set[str] = set()
        self.items_no = 0

    def album(self, album_name: str, page: int = 1) -> None:
        entry_id = f'{album_name}:{page}'
        if entry_id in self.generated:
            return
        self.generated.add(entry_id)

        if page == 1:
            print(album_name, end=' ')

        data = webxiang.get_data(
            album=album_name,
            page=page,
            staticgen=True,
            relative_links=self.opts['relative_links'],
        )
        if not data:
            if page == 1:
                logger.warning('album not found: %s', album_name)
            return

        if page > 1:
            name = _('page-%(number)s.html') % {'number': page}
        else:
            name = 'index.html'
        output_file = os.path.join(self.output_dir, album_name, name)
        self._progress(output_file, print_level=2)
        self._write(output_file, self._render(data))

        # symlink '/index.html' to '/index/index.html'
        if album_name == 'index' and page == 1:
            os.symlink('index/index.html', os.path.join(self.output_dir, 'index.html'))

        entries = cast(Page[Entry], data['entries'])
        for i in cast(Any, entries.paginator).page_range_limited:
            self.album(album_name, page=i)

        for entry in entries:
            if 'album' in entry:
                self.album(entry['album'])
            else:
                self.photo(album_name, f'{entry["index"]}/')

    def photo(self, album_name: str, entry_idx: str) -> None:
        entry_id = f'{album_name}/{entry_idx}'
        if entry_id in self.generated:
            return
        self.generated.add(entry_id)

        data = webxiang.get_data(
            album=album_name,
            photo=entry_idx,
            staticgen=True,
            relative_links=self.opts['relative_links'],
        )
        if not data:
            logger.warning('photo not found: %s/%s', album_name, entry_idx)
            return

        photo_idx = entry_idx.split('/')[0]
        entry = data['entry']
        if 'slug' in entry:
            photo_name = f'{photo_idx}/{entry["slug"]}.html'
        else:
            photo_name = f'{photo_idx}.html'

        output_file = os.path.join(self.output_dir, album_name, photo_name)
        self._progress(output_file, print_level=3)
        self._write(output_file, self._render(data))

    def _render(self, data: Album) -> str:
        tpl = data['meta'].get('template') or 'default.html'
        if not tpl.endswith('.html'):
            tpl += '.html'

        assets_url = self.opts['assets_url']
        settings.STATIC_URL = assets_url

        try:
            html = cast(str, render_to_string(tpl, cast(dict, data)))
        except TemplateDoesNotExist:
            html = cast(str, render_to_string('default.html', cast(dict, data)))

        if self.opts['relative_links']:
            html = html.replace('/' + assets_url, '../' + assets_url)
        return html

    def _progress(self, output_file: str, print_level: int) -> None:
        if self.opts['verbose'] >= print_level:
            print(f'writing {output_file}')
        elif self.opts['verbose'] >= 1:
            sys.stdout.write('.')
            sys.stdout.flush()

    def _write(self, output_file: str, html: str) -> None:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        self.items_no += 1


def _copytree(src: str, dst: str) -> None:
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)


if __name__ == '__main__':
    main()
