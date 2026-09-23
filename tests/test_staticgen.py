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

import json
import os
import re
import shutil
import socketserver
from pathlib import Path

import pytest
from django.conf import settings as django_settings
from django.core.cache import cache
from django.test import override_settings
from django.urls import get_script_prefix, get_urlconf
from django.utils import translation

from tests.conftest import SAMPLE_ALBUM_DIR, SAMPLE_PHOTO_ROOT


@pytest.fixture
def staticgen(monkeypatch, tmp_path):
    """The staticgen module, reading the sample albums and photos.

    Importing it points DJANGO_SETTINGS_MODULE at `webxiang.settings`, and
    serving changes the working directory; both are restored."""
    monkeypatch.setenv('DJANGO_SETTINGS_MODULE', os.environ['DJANGO_SETTINGS_MODULE'])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('signal.signal', lambda signum, handler: None)

    from tools import staticgen

    cache.clear()
    with override_settings(
        ALBUM_DIR=str(SAMPLE_ALBUM_DIR),
        WEBXIANG_PHOTOS_ROOT=str(SAMPLE_PHOTO_ROOT),
    ):
        yield staticgen
    cache.clear()


def _write_album(album_dir: Path, name: str, album: dict) -> None:
    (album_dir / f'{name}.json').write_text(json.dumps(album), encoding='utf-8')


def _gallery(tmp_path: Path) -> Path:
    """A --quick folder: album files and photos side by side, the top album
    named after the folder. album-one has two pages and a photo with a slug."""
    gallery = tmp_path / 'gallery'
    gallery.mkdir()
    for photo in SAMPLE_PHOTO_ROOT.rglob('*.jpg'):
        shutil.copy(photo, gallery)
    for name in ('index', 'album-one'):
        album = json.loads((SAMPLE_ALBUM_DIR / f'{name}.json').read_text())
        for key in ('path', 'path_thumb'):
            album['meta'].pop(key, None)
        if name == 'album-one':
            album['meta']['ppp'] = 2
            album['entries'][0]['slug'] = 'first'
        _write_album(gallery, name, album)
    shutil.copy(gallery / 'index.json', gallery / 'gallery.json')
    return gallery


_LINK = re.compile(r'(?:src|href)="([^"#?]*)"|"(?:url|url_full|link)": "([^"]*)"')


def _broken_links(output: Path) -> list[str]:
    """Local links in the pages under `output` that lead to no file, as
    'page: link'. Root-relative links are resolved against `output`."""
    broken = []
    for page in output.rglob('*.html'):
        if 'data' in page.parts or 'assets' in page.parts:
            continue
        for match in _LINK.finditer(page.read_text(encoding='utf-8')):
            link = match[1] or match[2]
            if link.startswith(('http:', 'https:', '//')):
                continue
            if link.startswith('/'):
                target = output / link.lstrip('/')
            else:
                target = page.parent / link
            if not link or link.endswith('/'):
                target /= 'index.html'
            if not os.path.exists(os.path.normpath(target)):
                broken.append(f'{page.relative_to(output)}: {link}')
    return broken


def _opts(staticgen, **kwargs):
    return staticgen.Options(**kwargs)


def _global_state() -> tuple:
    """What rendering pages changes and must put back."""
    return (
        django_settings.ALBUM_DIR,
        django_settings.STATIC_URL,
        django_settings.WEBXIANG_PHOTOS_URL,
        get_urlconf(),
        get_script_prefix(),
        translation.get_language(),
    )


def test_parse_args_applies_options(staticgen):
    opts = staticgen.parse_args(
        [
            '-v',
            '2',
            '--lang=pl',
            '--album-dir=albums',
            '--photo-dir=photos',
            '--root=/site',
            '--assets-url=/assets',
            '--photos-url=/photos',
            '--copy',
            '-p',
            '9000',
            'one,two',
            'out',
        ],
    )

    assert opts == staticgen.Options(
        verbose=2,
        lang='pl',
        album_dir_in='albums',
        photo_dir_in='photos',
        root='/site/',
        assets_url='/assets/',
        photos_url='/photos/',
        copy=True,
        port=9000,
        names='one,two',
        output_dir='out',
    )
    assert (opts.assets_dir, opts.photo_dir_out) == ('assets/', 'photos/')


def test_parse_args_puts_relative_urls_under_the_root(staticgen):
    opts = staticgen.parse_args(
        ['--root=/site', '--assets-url=assets', '--photos-url=https://cdn/p']
    )

    assert opts.assets_url == '/site/assets/'
    assert opts.photos_url == 'https://cdn/p/'
    assert opts.assets_dir == 'site/assets/'


def test_parse_args_quick_and_relative_links(staticgen):
    opts = staticgen.parse_args(
        ['--relative-links', '--quick=~/photos/trip/', '-s', 'site', 'other', 'out']
    )

    quick = os.path.expanduser('~/photos/trip')
    source = os.path.relpath(quick) + '/'
    assert opts == staticgen.Options(
        relative_links=True,
        quick=quick,
        names='trip',
        album_dir_in=source,
        photo_dir_in=source,
        assets_url='/assets/',
        photos_url='/trip/data/',
        serve='site',
    )
    assert (opts.assets_dir, opts.photo_dir_out) == ('assets/', 'trip/data/')


def test_parse_args_quick_keeps_photos_under_the_album_name(staticgen):
    opts = staticgen.parse_args(['--root=/site/', '--quick=trip'])

    assert (opts.assets_url, opts.photos_url) == ('/site/assets/', '/site/trip/data/')
    assert (opts.assets_dir, opts.photo_dir_out) == ('site/assets/', 'site/trip/data/')


def test_parse_args_defaults_to_index(staticgen):
    opts = staticgen.parse_args(['--root='])

    assert opts == staticgen.Options(root='')
    assert opts.album_dir_in == str(SAMPLE_ALBUM_DIR)


def test_parse_args_output_dir_option(staticgen):
    opts = staticgen.parse_args(['--output-dir=out', 'one'])

    assert (opts.names, opts.output_dir) == ('one', 'out')


def test_main_prints_help(staticgen, capsys):
    with pytest.raises(SystemExit) as exc:
        staticgen.main(['--help'])

    assert exc.value.code == 0
    assert 'default: output-DATETIME/' in capsys.readouterr().out


@pytest.mark.parametrize(
    ('argv', 'error'),
    [
        (['-y'], 'unrecognized arguments: -y'),
        (['--port=http'], "invalid int value: 'http'"),
        (['--serve'], 'argument -s/--serve: expected one argument'),
        (['a', 'b', 'c'], 'unrecognized arguments: c'),
    ],
)
def test_main_rejects_bad_arguments(staticgen, argv, error, capsys):
    with pytest.raises(SystemExit) as exc:
        staticgen.main(argv)

    assert exc.value.code == 2
    assert error in capsys.readouterr().err


def test_main_serve_only_serves_the_directory(staticgen, monkeypatch):
    served = []
    monkeypatch.setattr(staticgen, 'serve', lambda opts, root: served.append(root))

    with pytest.raises(SystemExit) as exc:
        staticgen.main(['--serve=site'])

    assert exc.value.code == 0
    assert served == ['site']


@pytest.mark.parametrize('relative_links', [False, True])
def test_main_quick_renders_the_gallery(
    staticgen, tmp_path, monkeypatch, capsys, relative_links
):
    gallery = _gallery(tmp_path)
    output = tmp_path / 'site'
    served = []
    monkeypatch.setattr(staticgen, 'serve', lambda opts, root: served.append(root))

    argv = ['-v', '2', f'--quick={gallery}', f'--output-dir={output}']
    if relative_links:
        argv.append('--relative-links')
    staticgen.main(argv)

    assert served == [str(output)]
    assert sorted(
        str(path.relative_to(output))
        for path in output.rglob('*.html')
        if 'data' not in path.parts
    ) == [
        'album-one/1/first.html',
        'album-one/2.html',
        'album-one/3.html',
        'album-one/index.html',
        'album-one/page-2.html',
        'gallery/index.html',
        'index.html',
    ]
    assert (output / 'gallery' / 'data' / 'dsc08340.jpg').exists()
    assert (output / 'assets' / 'staticfiles.json').exists()
    assert _broken_links(output) == []

    photo = (output / 'album-one' / '1' / 'first.html').read_text(encoding='utf-8')
    if relative_links:
        assert not (output / 'index.html').is_symlink()
        assert 'href="../../assets/css/' in photo
        assert 'href="../../album-one/2.html"' in photo
        assert 'href="../../index.html"' in photo
    else:
        assert os.readlink(output / 'index.html') == 'gallery/index.html'
        assert 'href="/assets/css/' in photo
        assert 'href="/album-one/2.html"' in photo
        assert 'href="/"' in photo
    files = 7 if relative_links else 6
    assert capsys.readouterr().out.endswith(f'Done. Created {files} files.\n')


def test_relative_urls_follow_the_page_depth(staticgen):
    html = (
        '<a href="/">home</a> <a href="/trip/">trip</a> <img src="/data/a.jpg">'
        ' <a href="//cdn/x.js"></a> <a href="page-2.html"></a> {"link": "/trip/2.html"}'
    )

    assert staticgen.relative_urls(html, 0) == (
        '<a href="index.html">home</a> <a href="trip/index.html">trip</a>'
        ' <img src="data/a.jpg"> <a href="//cdn/x.js"></a> <a href="page-2.html"></a>'
        ' {"link": "trip/2.html"}'
    )
    assert staticgen.relative_urls(html, 2).startswith(
        '<a href="../../index.html">home</a> <a href="../../trip/index.html">'
    )


def test_main_renders_albums_from_settings_under_a_root(
    staticgen, tmp_path, monkeypatch
):
    output = tmp_path / 'site'
    monkeypatch.setattr(staticgen, 'serve', lambda opts, root: None)
    before = _global_state()

    staticgen.main(['-v', '0', '--lang=pl', '--root=/sub/', 'index', str(output)])

    assert _global_state() == before
    assert (output / 'sub' / 'index' / 'index.html').exists()
    assert (output / 'data').is_symlink()
    assert (output / 'static' / 'staticfiles.json').exists()
    page = (output / 'sub' / 'album-one' / 'index.html').read_text(encoding='utf-8')
    assert 'href="/sub/album-one/1.html"' in page
    assert 'src="/data/' in page
    assert 'href="/static/css/' in page


def test_site_context_restores_state_after_errors(staticgen):
    before = _global_state()

    with (
        pytest.raises(RuntimeError),
        staticgen.site_context(_opts(staticgen, root='/x/', assets_url='/a/')),
    ):
        assert django_settings.STATIC_URL == '/a/'
        assert get_script_prefix() == '/x/'
        assert translation.get_language() == 'en'
        raise RuntimeError

    assert _global_state() == before


def test_publish_photos_copies_or_links(staticgen, tmp_path, caplog):
    source = tmp_path / 'photos'
    (source / 'sub').mkdir(parents=True)
    (source / 'a.jpg').write_bytes(b'a')
    (source / 'sub' / 'b.jpg').write_bytes(b'b')

    copied = tmp_path / 'out' / 'copied'
    staticgen.publish_photos(
        _opts(staticgen, copy=True, photo_dir_in=f'{source}/'), f'{copied}/'
    )
    assert (copied / 'a.jpg').read_bytes() == b'a'
    assert (copied / 'sub' / 'b.jpg').read_bytes() == b'b'

    linked = tmp_path / 'out' / 'nested' / 'linked'
    staticgen.publish_photos(_opts(staticgen, photo_dir_in=str(source)), f'{linked}/')
    assert linked.is_symlink()
    assert (linked / 'a.jpg').read_bytes() == b'a'

    # failures are reported, not raised
    staticgen.publish_photos(_opts(staticgen, photo_dir_in=str(source)), f'{linked}/')
    missing = str(tmp_path / 'missing')
    staticgen.publish_photos(
        _opts(staticgen, copy=True, photo_dir_in=missing), f'{copied}/'
    )
    with override_settings(STATIC_ROOT=missing):
        staticgen.copy_assets(str(tmp_path / 'assets'))

    assert [msg.split(' [Errno')[0] for msg in caplog.messages] == [
        'cannot link photos:',
        'cannot copy photos:',
        'cannot copy assets:',
    ]


def test_site_generator_writes_pages_photos_and_index_link(
    staticgen, tmp_path, capsys, caplog
):
    album_dir = tmp_path / 'albums'
    album_dir.mkdir()
    _write_album(
        album_dir,
        'index',
        {
            'meta': {'title': 'Home', 'template': 'missing-template', 'ppp': 1},
            'entries': [{'album': 'trip'}, {'album': 'nowhere'}],
        },
    )
    _write_album(
        album_dir,
        'trip',
        {
            'meta': {'title': 'Trip', 'template': 'floating', 'ppp': 2},
            'entries': [
                {'image': 'one.jpg', 'slug': 'first'},
                {'image': 'two.jpg'},
                {'image': 'three.jpg'},
            ],
        },
    )
    output = tmp_path / 'site'

    opts = _opts(staticgen, verbose=3, album_dir_in=str(album_dir))
    with staticgen.site_context(opts):
        generator = staticgen.SiteGenerator(opts, str(output))
        generator.album('index')
        generator.album('index')  # already done
        generator.photo('trip', '99/')  # no such photo

    assert generator.items_no == 7
    assert sorted(str(p.relative_to(output)) for p in output.rglob('*.html')) == [
        'index.html',
        'index/index.html',
        'index/page-2.html',
        'trip/1/first.html',
        'trip/2.html',
        'trip/3.html',
        'trip/index.html',
        'trip/page-2.html',
    ]
    assert os.readlink(output / 'index.html') == 'index/index.html'
    out = capsys.readouterr().out
    assert out.startswith('index writing ')
    assert 'trip writing ' in out
    assert 'nowhere ' in out
    assert 'writing %s' % (output / 'trip' / '2.html') in out
    assert caplog.messages == ['album not found: nowhere', 'photo not found: trip/99/']


def test_site_generator_progress_dots(staticgen, capsys):
    quiet = staticgen.SiteGenerator(_opts(staticgen, verbose=0))
    dots = staticgen.SiteGenerator(_opts(staticgen, verbose=2))

    quiet._progress('a.html', print_level=2)
    dots._progress('b.html', print_level=3)
    dots._progress('c.html', print_level=2)

    assert capsys.readouterr().out == '.writing c.html\n'


def test_serve_changes_directory_and_serves(staticgen, tmp_path, monkeypatch, capsys):
    served = []

    def serve_forever(server, *args):
        served.append(server.server_address[0])
        server.server_close()

    monkeypatch.setattr(socketserver.BaseServer, 'serve_forever', serve_forever)
    (tmp_path / 'site').mkdir()

    staticgen.serve(_opts(staticgen, port=0), str(tmp_path / 'site'))

    assert served == ['127.0.0.1']
    assert Path.cwd() == (tmp_path / 'site').resolve()
    assert 'Serving at localhost:0/' in capsys.readouterr().out


def test_quit_app_exits(staticgen):
    with pytest.raises(SystemExit) as exc:
        staticgen._quit_app(3)

    assert exc.value.code == 3


def test_main_quick_defaults_to_a_dated_output_dir(
    staticgen, tmp_path, monkeypatch, capsys
):
    gallery = _gallery(tmp_path)
    monkeypatch.setattr(staticgen, 'serve', lambda opts, root: None)

    staticgen.main(['-v', '0', '--lang=pl', f'--quick={gallery}'])

    (output,) = tmp_path.glob('output-*')
    assert (output / 'gallery' / 'index.html').exists()
    assert (output / 'album-one' / '2.html').exists()
    # no progress dots, no blank line before the summary
    assert 'Generating static pages.\ngallery album-one Finished' in (
        capsys.readouterr().out
    )
