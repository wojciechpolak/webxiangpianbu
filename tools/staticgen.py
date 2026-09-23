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
import re
import shutil
import signal
import socketserver
import sys
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from typing import Any, NoReturn, cast
from urllib.parse import urljoin, urlparse

import django
from django.conf import settings
from django.core.paginator import Page
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.test import override_settings
from django.urls import get_script_prefix, set_script_prefix, set_urlconf
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


def _setting(name: str, default: str) -> Callable[[], str]:
    return lambda: getattr(settings, name, default)


@dataclass(frozen=True)
class Options:
    verbose: int = 1
    output_dir: str | None = None
    album_dir_in: str = field(default_factory=_setting('ALBUM_DIR', 'albums'))
    photo_dir_in: str = field(default_factory=_setting('WEBXIANG_PHOTOS_ROOT', ''))
    root: str = '/'
    assets_url: str = field(default_factory=_setting('STATIC_URL', 'assets/'))
    photos_url: str = field(default_factory=_setting('WEBXIANG_PHOTOS_URL', 'data/'))
    relative_links: bool = False
    names: str = 'index'
    lang: str = 'en'
    quick: str | None = None
    copy: bool = False
    serve: str | None = None
    port: int = 8000

    @property
    def assets_dir(self) -> str:
        """Where assets go, relative to the output root."""
        return urlparse(self.assets_url).path.lstrip('/')

    @property
    def photo_dir_out(self) -> str:
        """Where photos go, relative to the output root."""
        return urlparse(self.photos_url).path.lstrip('/')


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
        help='link pages relative to each other, so the site works from any '
        'directory or without a web server; ignores --root',
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
    parser.set_defaults(**asdict(Options()))
    return parser


def parse_args(argv: list[str]) -> Options:
    args = vars(build_parser().parse_args(argv))
    output = args.pop('output')
    opts = Options(**args)
    if opts.relative_links:
        opts = replace(opts, root='/')
    if opts.quick:
        opts = quick_options(opts, opts.quick)
    elif output:
        opts = replace(opts, output_dir=output)
    return replace(
        opts,
        assets_url=urljoin(opts.root, opts.assets_url),
        photos_url=urljoin(opts.root, opts.photos_url),
    )


def quick_options(opts: Options, folder: str) -> Options:
    """--quick: album files and photos both in `folder`, the album named after
    it rendered first, assets and photos kept next to the pages."""
    name = os.path.basename(folder)
    source = os.path.relpath(folder, os.getcwd()) + '/'
    return replace(
        opts,
        names=name,
        album_dir_in=source,
        photo_dir_in=source,
        assets_url='assets/',
        photos_url=os.path.join(name, 'data/'),
    )


def main(argv: list[str] | None = None) -> None:
    opts = parse_args(sys.argv[1:] if argv is None else argv)

    signal.signal(signal.SIGTERM, lambda signum, frame: _quit_app())
    signal.signal(signal.SIGINT, lambda signum, frame: _quit_app())

    if opts.serve:
        serve(opts, opts.serve)
        sys.exit(0)

    root_dir = (
        os.path.expanduser(opts.output_dir)
        if opts.output_dir
        else f'output-{datetime.now().astimezone():%Y%m%d-%H%M%S}'
    )
    output_dir = os.path.join(root_dir, opts.root.lstrip('/'))

    if opts.verbose > 1:
        print('OPTIONS', json.dumps(asdict(opts), indent=2, sort_keys=True))

    if not os.path.exists(output_dir):
        print(f'Creating directory "{output_dir}"')
        with contextlib.suppress(OSError):
            os.makedirs(output_dir)

    if not opts.photos_url.startswith('http'):
        publish_photos(opts, os.path.join(root_dir, opts.photo_dir_out))
    copy_assets(os.path.join(root_dir, opts.assets_dir))

    if opts.lang and opts.verbose > 1:
        print(f'Switching language to {opts.lang}')
    print('Generating static pages.')
    album_names = opts.names.split(',')
    with site_context(opts):
        generator = SiteGenerator(opts, output_dir, home=album_names[0])
        for album_name in album_names:
            generator.album(album_name)

    if opts.verbose > 0:
        print()
    print(f'Finished {output_dir}')
    print(f'Done. Created {generator.items_no:d} files.')

    serve(opts, root_dir)


@contextlib.contextmanager
def site_context(opts: Options) -> Iterator[None]:
    """The settings, urlconf, script prefix and language pages are rendered
    with, all restored afterwards."""
    language = (
        translation.override(opts.lang, deactivate=True)
        if opts.lang
        else contextlib.nullcontext()
    )
    script_prefix = get_script_prefix()
    set_urlconf('webxiang.urls_static')
    set_script_prefix(opts.root)
    try:
        with (
            language,
            override_settings(
                ALBUM_DIR=opts.album_dir_in,
                WEBXIANG_PHOTOS_URL=opts.photos_url,
                STATIC_URL=opts.assets_url,
            ),
        ):
            yield
    finally:
        set_urlconf(None)
        set_script_prefix(script_prefix)


def publish_photos(opts: Options, photo_dir_out: str) -> None:
    """Copy (--copy) or symlink the photo directory into the output."""
    photo_dir_in = opts.photo_dir_in.rstrip('/')
    if opts.copy:
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
            os.symlink(os.path.abspath(photo_dir_in), link)
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


def serve(opts: Options, root_dir: str | None = None) -> None:
    class SimpleServer(socketserver.TCPServer):
        allow_reuse_address = True

    if root_dir:
        os.chdir(root_dir)

    httpd = SimpleServer(('localhost', opts.port), http.server.SimpleHTTPRequestHandler)
    print(f'Serving at localhost:{opts.port:d}{opts.root}')
    print('Quit the server with CONTROL-C.')
    httpd.serve_forever()


class SiteGenerator:
    """Renders albums and their photos into `output_dir`, each page once.
    The first page of the `home` album is also the site's `index.html`."""

    def __init__(self, opts: Options, output_dir: str = '.', home: str = 'index'):
        self.opts = opts
        self.output_dir = output_dir
        self.home = home
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
        html = self._render(data)
        self._write(output_file, html)

        if album_name == self.home and page == 1:
            self._home(album_name, html)

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

    def _home(self, album_name: str, html: str) -> None:
        home = os.path.join(self.output_dir, 'index.html')
        if self.opts.relative_links:
            self._write(home, html)  # a link would resolve its URLs one level up
        else:
            os.symlink(f'{album_name}/index.html', home)

    def _render(self, data: Album) -> str:
        """The page's HTML, its links rooted at the site root."""
        tpl = data['meta'].get('template') or 'default.html'
        if not tpl.endswith('.html'):
            tpl += '.html'

        try:
            html = cast(str, render_to_string(tpl, cast(dict, data)))
        except TemplateDoesNotExist:
            html = cast(str, render_to_string('default.html', cast(dict, data)))
        return html

    def _progress(self, output_file: str, print_level: int) -> None:
        if self.opts.verbose >= print_level:
            print(f'writing {output_file}')
        elif self.opts.verbose >= 1:
            sys.stdout.write('.')
            sys.stdout.flush()

    def _write(self, output_file: str, html: str) -> None:
        if self.opts.relative_links:
            depth = os.path.relpath(output_file, self.output_dir).count(os.sep)
            html = relative_urls(html, depth)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        self.items_no += 1


_ROOT_URL = re.compile(r'"/(?!/)([^"]*)"')


def relative_urls(html: str, depth: int) -> str:
    """`html` with its quoted root-relative URLs, like "/album/", made
    relative to a page `depth` directories below the root. Directory URLs
    get `index.html` added, so the pages work without a web server."""
    prefix = '../' * depth

    def relative(match: re.Match[str]) -> str:
        path = match[1]
        if not path or path.endswith('/'):
            path += 'index.html'
        return f'"{prefix}{path}"'

    return _ROOT_URL.sub(relative, html)


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
