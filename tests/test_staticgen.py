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
import shutil
import socketserver
from pathlib import Path

import pytest
from django.conf import settings as django_settings
from django.core.cache import cache
from django.test import override_settings
from django.urls import set_script_prefix, set_urlconf
from django.utils import translation

from tests.conftest import SAMPLE_ALBUM_DIR, SAMPLE_PHOTO_ROOT


@pytest.fixture
def staticgen(monkeypatch, tmp_path):
    """The staticgen module, with the global state it touches restored.

    Importing it points DJANGO_SETTINGS_MODULE at `webxiang.settings`, and a
    run changes settings, the urlconf, the script prefix, the language and
    the working directory."""
    monkeypatch.setenv('DJANGO_SETTINGS_MODULE', os.environ['DJANGO_SETTINGS_MODULE'])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('signal.signal', lambda signum, handler: None)

    from tools import staticgen

    cache.clear()
    # Overriding STATIC_URL, even to itself, drops the cached staticfiles
    # storage. Staticgen needs one created after it sets its assets URL.
    with override_settings(
        ALBUM_DIR=str(SAMPLE_ALBUM_DIR),
        WEBXIANG_PHOTOS_ROOT=str(SAMPLE_PHOTO_ROOT),
        STATIC_URL=django_settings.STATIC_URL,
    ):
        yield staticgen
    cache.clear()
    set_urlconf(None)
    set_script_prefix('/')
    translation.deactivate()


def _gallery(tmp_path: Path) -> Path:
    """A --quick folder: album files and photos side by side, the top album
    named after the folder."""
    gallery = tmp_path / 'gallery'
    shutil.copytree(SAMPLE_PHOTO_ROOT, gallery)
    for album in SAMPLE_ALBUM_DIR.glob('*.json'):
        shutil.copy(album, gallery)
    shutil.copy(SAMPLE_ALBUM_DIR / 'index.json', gallery / 'gallery.json')
    return gallery


def _opts(staticgen, **kwargs) -> dict:
    opts: dict = staticgen.default_opts()
    opts.update(kwargs)
    return opts


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

    assert opts['verbose'] == 2
    assert opts['lang'] == 'pl'
    assert opts['album_dir_in'] == 'albums'
    assert opts['photo_dir_in'] == 'photos'
    assert opts['root'] == '/site/'
    assert opts['assets_url'] == '/assets/'
    assert opts['photos_url'] == '/photos/'
    assert opts['copy'] is True
    assert opts['port'] == 9000
    assert opts['names'] == 'one,two'
    assert opts['output_dir'] == 'out'


def test_parse_args_quick_and_relative_links(staticgen):
    opts = staticgen.parse_args(
        ['--relative-links', '--quick=~/photos/trip/', '-s', 'site', 'other', 'out']
    )

    assert opts['relative_links'] is True
    assert opts['root'] == ''
    assert opts['quick'] == os.path.expanduser('~/photos/trip')
    assert opts['names'] == 'trip'
    assert opts['serve'] == 'site'
    assert opts['output_dir'] is None


def test_parse_args_defaults_to_index(staticgen):
    opts = staticgen.parse_args(['--root='])

    assert opts == {**staticgen.default_opts(), 'root': ''}


def test_parse_args_output_dir_option(staticgen):
    opts = staticgen.parse_args(['--output-dir=out', 'one'])

    assert (opts['names'], opts['output_dir']) == ('one', 'out')


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
        'album-one/1.html',
        'album-one/2.html',
        'album-one/3.html',
        'album-one/index.html',
        'gallery/index.html',
    ]
    assert (output / 'gallery' / 'data').is_symlink()
    assert (output / 'assets' / 'staticfiles.json').exists()

    photo = (output / 'album-one' / '2.html').read_text(encoding='utf-8')
    if relative_links:
        assert '../assets/' in photo
        assert 'href="3.html"' in photo
    else:
        assert '/assets/' in photo
        assert 'href="/album-one/3.html"' in photo
    assert capsys.readouterr().out.endswith('Done. Created 5 files.\n')


def test_configure_urls_prefixes_root_when_not_relative(staticgen):
    opts = _opts(staticgen, root='/site/', assets_url='assets/', photos_url='data/')

    staticgen.configure_urls(opts)

    assert opts['assets_url'] == '/site/assets/'
    assert opts['photos_url'] == '/site/data/'
    assert django_settings.WEBXIANG_PHOTOS_URL == '/site/data/'


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


def _write_album(album_dir: Path, name: str, album: dict) -> None:
    (album_dir / f'{name}.json').write_text(json.dumps(album), encoding='utf-8')


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

    with override_settings(ALBUM_DIR=str(album_dir)):
        generator = staticgen.SiteGenerator(
            _opts(staticgen, verbose=3, assets_url='/assets/'), str(output)
        )
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
    assert (output / 'album-one' / '1.html').exists()
    # no progress dots, no blank line before the summary
    assert 'Generating static pages.\ngallery album-one Finished' in (
        capsys.readouterr().out
    )
