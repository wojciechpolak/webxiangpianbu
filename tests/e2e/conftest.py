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
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings as django_settings
from django.core.management import call_command
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)
from tests.e2e.vrt import VisualRegressionSession

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / 'test-results' / 'playwright'
VRT_ARTIFACTS_DIR = ROOT / 'test-results' / 'vrt'
SAMPLE_MEDIA_ROOT = ROOT / 'run' / 'data'


def _slugify_nodeid(nodeid: str) -> str:
    return re.sub(r'[^A-Za-z0-9_.-]+', '-', nodeid).strip('-')


def _env_flag(name: str) -> bool:
    value = os.environ.get(name, '')
    return value.lower() in {'1', 'true', 'yes', 'on'}


def _build_sample_site(root: Path) -> tuple[Path, Path]:
    album_dir = root / 'albums'
    photo_root = root / 'data'
    album_dir.mkdir(parents=True, exist_ok=True)
    photo_root.mkdir(parents=True, exist_ok=True)

    (album_dir / 'index.json').write_text(
        json.dumps(
            {
                'meta': {
                    'path': 'tiny/',
                    'style': 'light.css',
                    'title': 'Photo Albums',
                    'robots': 'index,nofollow',
                    'copyright': '2007',
                    'columns': 3,
                    'ppp': 36,
                    'default_thumb_size': [300, 200],
                    'custom_menu': False,
                    'custom_css': '',
                },
                'entries': [
                    {
                        'album': 'album-one',
                        'thumb': {
                            'path': '2007-01-fireworks/',
                            'file': 'dsc08340-300x200.jpg',
                        },
                        'comment': 'First Album: Fireworks!',
                    }
                ],
            }
        ),
        encoding='utf-8',
    )
    (album_dir / 'album-one.json').write_text(
        json.dumps(
            {
                'meta': {
                    'style': 'base.css',
                    'path': '2007-01-fireworks/',
                    'path_thumb': '2007-01-fireworks/tiny/',
                    'ppp': 15,
                    'columns': 3,
                    'title': 'Fireworks',
                    'cover': 'tiny-dsc08340.jpg',
                    'copyright': '2007 WAP',
                    'default_thumb_size': [200, 133],
                },
                'entries': [
                    {
                        'thumb': 'tiny-dsc08340.jpg',
                        'image': 'dsc08340.jpg',
                        'copyright': '2007 WAP',
                    },
                    {
                        'thumb': 'tiny-dsc08340.jpg',
                        'image': 'dsc08340.jpg',
                        'copyright': '2007 WAP',
                    },
                    {
                        'thumb': 'tiny-dsc08340.jpg',
                        'image': 'dsc08340.jpg',
                        'copyright': '2007 WAP',
                    },
                ],
            }
        ),
        encoding='utf-8',
    )
    (album_dir / 'story-album.json').write_text(
        json.dumps(
            {
                'meta': {
                    'title': 'Story Album',
                    'template': 'story',
                    'style': 'dark',
                    'copyright': '2024 Example',
                    'copyright_link': '/',
                    'custom_menu': True,
                    'prev_story': 'album-one',
                },
                'entries': [
                    {
                        'video': [
                            {
                                'src': '/data/story/story.webm',
                                'media': '(min-width: 1000px)',
                                'type': 'video/webm',
                            },
                            {
                                'src': '/data/story/story.mp4',
                                'type': 'video/mp4',
                            },
                        ],
                        'video_preload': True,
                        'video_download': '/data/story/story.mp4',
                        'poster': '/data/2007-01-fireworks/dsc08340-300x200.jpg',
                        'slug': 'story',
                    }
                ],
            }
        ),
        encoding='utf-8',
    )

    for rel_path in [
        '2007-01-fireworks/dsc08340.jpg',
        '2007-01-fireworks/dsc08340-300x200.jpg',
        '2007-01-fireworks/tiny/tiny-dsc08340.jpg',
        'story/story.webm',
        'story/story.mp4',
        'story/story.jpg',
    ]:
        asset = photo_root / rel_path
        asset.parent.mkdir(parents=True, exist_ok=True)
        sample_source = SAMPLE_MEDIA_ROOT / rel_path
        if sample_source.exists():
            shutil.copyfile(sample_source, asset)
        elif rel_path == 'story/story.jpg':
            shutil.copyfile(
                SAMPLE_MEDIA_ROOT / '2007-01-fireworks/dsc08340-300x200.jpg',
                asset,
            )
        else:
            asset.write_bytes(b'placeholder')

    return album_dir, photo_root


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f'rep_{report.when}', report)


@pytest.fixture(scope='session')
def sample_site_root(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp('e2e-site')
    return _build_sample_site(root)


@pytest.fixture(scope='session', autouse=True)
def e2e_runtime_settings(
    sample_site_root: tuple[Path, Path], tmp_path_factory: pytest.TempPathFactory
) -> Generator[None, None, None]:
    album_dir, photo_root = sample_site_root
    root = tmp_path_factory.mktemp('e2e-runtime')
    static_root = root / 'static'
    session_root = root / 'sessions'
    static_root.mkdir(parents=True, exist_ok=True)
    session_root.mkdir(parents=True, exist_ok=True)

    django_settings.ALLOWED_HOSTS = list(
        dict.fromkeys(
            [*django_settings.ALLOWED_HOSTS, 'testserver', 'localhost', '127.0.0.1']
        )
    )
    django_settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }
    django_settings.ALBUM_DIR = str(album_dir)
    django_settings.WEBXIANG_PHOTOS_ROOT = str(photo_root)
    django_settings.WEBXIANG_PHOTOS_URL = '/data/'
    django_settings.MEDIA_URL = '/media/'
    django_settings.SESSION_ENGINE = 'django.contrib.sessions.backends.file'
    django_settings.SESSION_FILE_PATH = str(session_root)
    django_settings.SITE_URL = 'https://www.example.org/'
    django_settings.STATIC_ROOT = str(static_root)
    call_command('collectstatic', interactive=False, verbosity=0, clear=True)
    yield


@pytest.fixture(scope='session', autouse=True)
def clean_e2e_artifacts() -> Generator[None, None, None]:
    for path in (ARTIFACTS_DIR, VRT_ARTIFACTS_DIR):
        shutil.rmtree(path, ignore_errors=True)
    yield


@pytest.fixture(scope='session')
def playwright_instance() -> Generator[Playwright, None, None]:
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture
def browser(playwright_instance: Playwright) -> Generator[Browser, None, None]:
    browser = playwright_instance.chromium.launch(
        headless=not _env_flag('WEBXIANG_E2E_HEADED'),
        slow_mo=int(os.environ.get('WEBXIANG_E2E_SLOWMO_MS', '0')),
    )
    yield browser
    browser.close()


@pytest.fixture
def page(
    browser: Browser, request: pytest.FixtureRequest
) -> Generator[Page, None, None]:
    node_slug = _slugify_nodeid(request.node.nodeid)
    test_artifacts = ARTIFACTS_DIR / node_slug
    test_artifacts.mkdir(parents=True, exist_ok=True)

    context: BrowserContext = browser.new_context(
        viewport={'width': 1440, 'height': 960}
    )
    if _env_flag('VRT'):
        context.add_init_script(
            """
            (() => {
                const disableEffects = () => {
                    if (window.jQuery && window.jQuery.fx) {
                        window.jQuery.fx.off = true;
                        return true;
                    }
                    return false;
                };

                if (disableEffects()) {
                    return;
                }

                let attempts = 0;
                const timer = window.setInterval(() => {
                    attempts += 1;
                    if (disableEffects() || attempts > 200) {
                        window.clearInterval(timer);
                    }
                }, 5);
            })();
            """
        )
    context.tracing.start(screenshots=True, snapshots=True)
    page = context.new_page()

    yield page

    failed = bool(
        getattr(request.node, 'rep_call', None) and request.node.rep_call.failed
    )
    if failed:
        page.screenshot(path=str(test_artifacts / 'failure.png'), full_page=True)
        context.tracing.stop(path=str(test_artifacts / 'trace.zip'))
    else:
        context.tracing.stop()
    context.close()


@pytest.fixture
def vrt(request: pytest.FixtureRequest) -> VisualRegressionSession:
    return VisualRegressionSession.from_request(request)
