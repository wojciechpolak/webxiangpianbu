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
import tempfile
from pathlib import Path

import pytest
from django.test import LiveServerTestCase, override_settings
from playwright.sync_api import expect, sync_playwright

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

pytestmark = pytest.mark.e2e


class BrowserFlowsTest(LiveServerTestCase):
    _tempdir: tempfile.TemporaryDirectory[str] | None = None

    @classmethod
    def _build_sample_site(cls) -> tuple[Path, Path]:
        tempdir = tempfile.TemporaryDirectory()
        cls._tempdir = tempdir
        root = Path(tempdir.name)
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
                            'poster': '/data/story/story.jpg',
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
            asset.write_bytes(b'placeholder')

        return album_dir, photo_root

    @classmethod
    def setUpClass(cls):
        cls._album_dir, cls._photo_root = cls._build_sample_site()
        cls._override = override_settings(
            ALBUM_DIR=str(cls._album_dir),
            WEBXIANG_PHOTOS_ROOT=str(cls._photo_root),
            WEBXIANG_PHOTOS_URL='/data/',
            SITE_URL='https://www.example.org/',
        )
        cls._override.enable()
        super().setUpClass()
        cls._playwright = sync_playwright().start()

    @classmethod
    def tearDownClass(cls):
        cls._playwright.stop()
        super().tearDownClass()
        cls._override.disable()
        assert cls._tempdir is not None
        cls._tempdir.cleanup()

    def setUp(self):
        self.browser = self._playwright.chromium.launch()
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 900})
        self.page = self.context.new_page()

    def tearDown(self):
        self.context.close()
        self.browser.close()

    def test_home_page_lists_sample_album(self):
        self.page.goto(self.live_server_url, wait_until='networkidle')

        expect(self.page).to_have_title('Photo Albums')
        expect(self.page.locator('a[href="/album-one/"]')).to_be_visible()

        with self.page.expect_navigation(wait_until='networkidle'):
            self.page.locator('a[href="/album-one/"]').click()

        expect(self.page).to_have_title('Fireworks')
        expect(self.page.locator('h2#title')).to_have_text('Fireworks')
        expect(self.page.locator('a[data-index="1"] img')).to_be_visible()

    def test_photo_page_has_prev_next_navigation(self):
        self.page.goto(f'{self.live_server_url}/album-one/1', wait_until='networkidle')

        expect(self.page).to_have_title('#1 - Fireworks')
        expect(self.page.locator('#prevPhoto')).to_have_count(0)
        expect(self.page.locator('#nextPhoto')).to_have_attribute(
            'href', '/album-one/2'
        )

        with self.page.expect_navigation(wait_until='networkidle'):
            self.page.locator('#nextPhoto').click()

        expect(self.page).to_have_url(f'{self.live_server_url}/album-one/2')
        expect(self.page).to_have_title('#2 - Fireworks')
        expect(self.page.locator('#prevPhoto')).to_have_attribute(
            'href', '/album-one/1'
        )

        with self.page.expect_navigation(wait_until='networkidle'):
            self.page.keyboard.press('u')

        expect(self.page).to_have_url(f'{self.live_server_url}/album-one/')
        expect(self.page).to_have_title('Fireworks')
        expect(self.page.locator('a[data-index="1"] img')).to_be_visible()

    def test_help_dialog_opens_and_closes_with_keyboard(self):
        self.page.goto(f'{self.live_server_url}/album-one/1', wait_until='networkidle')

        expect(self.page.locator('#help')).to_be_hidden()
        expect(self.page.locator('#overlay')).to_be_hidden()

        self.page.keyboard.press('h')

        expect(self.page.locator('#help')).to_be_visible()
        expect(self.page.locator('#overlay')).to_be_visible()

        self.page.keyboard.press('Escape')

        expect(self.page.locator('#help')).to_be_hidden()
        expect(self.page.locator('#overlay')).to_be_hidden()

    def test_story_album_exposes_story_navigation_and_html5_video(self):
        self.page.goto(f'{self.live_server_url}/story-album/', wait_until='networkidle')

        expect(self.page).to_have_title('Story Album')
        expect(self.page.locator('#prevStory')).to_have_attribute('href', '/album-one/')
        expect(self.page.locator('#nextStory')).to_have_count(0)
        expect(self.page.locator('.video.html5 video')).to_be_visible()
        expect(self.page.locator('.video.html5 source')).to_have_count(2)
        expect(self.page.locator('.download a')).to_have_attribute(
            'href', '/data/story/story.mp4'
        )
