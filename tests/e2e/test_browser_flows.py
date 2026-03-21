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

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def test_home_page_lists_sample_album(page, live_server, vrt):
    page.goto(live_server.url, wait_until='networkidle')

    expect(page).to_have_title('Photo Albums')
    expect(page.locator('a[href="/album-one/"]')).to_be_visible()
    vrt.screenshot(page.locator('#content'), 'main-stream.png')

    with page.expect_navigation(wait_until='networkidle'):
        page.locator('a[href="/album-one/"]').click()

    expect(page).to_have_title('Fireworks')
    expect(page.locator('h2#title')).to_have_text('Fireworks')
    expect(page.locator('a[data-index="1"] img')).to_be_visible()


def test_photo_page_has_prev_next_navigation(page, live_server, vrt):
    page.goto(f'{live_server.url}/album-one/1', wait_until='networkidle')

    expect(page).to_have_title('#1 - Fireworks')
    expect(page.locator('#prevPhoto')).to_have_count(0)
    expect(page.locator('#nextPhoto')).to_have_attribute('href', '/album-one/2')
    vrt.screenshot(
        page.locator('#content'),
        'photo-page.png',
        mask=[page.locator('#show-help')],
    )

    with page.expect_navigation(wait_until='networkidle'):
        page.locator('#nextPhoto').click()

    expect(page).to_have_url(f'{live_server.url}/album-one/2')
    expect(page).to_have_title('#2 - Fireworks')
    expect(page.locator('#prevPhoto')).to_have_attribute('href', '/album-one/1')

    with page.expect_navigation(wait_until='networkidle'):
        page.locator('#levelIndex').click()

    expect(page).to_have_url(f'{live_server.url}/album-one/')
    expect(page).to_have_title('Fireworks')
    expect(page.locator('a[data-index="1"] img')).to_be_visible()


def test_help_dialog_markup_is_present(page, live_server, vrt):
    page.goto(f'{live_server.url}/album-one/1', wait_until='networkidle')

    expect(page.locator('#show-help')).to_be_visible()
    expect(page.locator('#help')).to_be_hidden()
    expect(page.locator('#overlay')).to_be_hidden()
    expect(page.locator('#help')).to_contain_text('Keyboard Shortcuts')
    expect(page.locator('#help .close')).to_have_text('Close')
    page.evaluate(
        """
        () => {
            if (typeof window.showDialog === 'function') {
                window.showDialog('#help');
                return;
            }

            const help = document.getElementById('help');
            const overlay = document.getElementById('overlay');
            if (!help || !overlay) {
                return;
            }

            const height = window.innerHeight;
            const width = window.innerWidth;
            overlay.style.display = 'block';
            overlay.style.height = `${height}px`;
            overlay.style.width = `${width}px`;
            help.style.display = 'block';
            help.style.top = `${Math.max(
                0,
                (height / 2) - (help.offsetHeight / 1.5)
            ) + window.scrollY}px`;
            help.style.left = `${Math.max(
                0,
                (width / 2) - (help.offsetWidth / 2)
            )}px`;
        }
        """
    )
    expect(page.locator('#help')).to_be_visible()
    expect(page.locator('#overlay')).to_be_visible()
    page.wait_for_function(
        """
        () => {
            const help = document.querySelector('#help');
            return !!help && window.getComputedStyle(help).opacity === '1';
        }
        """
    )
    vrt.screenshot_locator(
        page.locator('#help .dialog-content'),
        'help-dialog.png',
    )


def test_story_album_exposes_story_navigation_and_html5_video(page, live_server, vrt):
    page.goto(f'{live_server.url}/story-album/', wait_until='networkidle')

    expect(page).to_have_title('Story Album')
    expect(page.locator('#prevStory')).to_have_attribute('href', '/album-one/')
    expect(page.locator('#nextStory')).to_have_count(0)
    expect(page.locator('.video.html5 video')).to_be_visible()
    expect(page.locator('.video.html5 source')).to_have_count(2)
    expect(page.locator('.download a')).to_have_attribute(
        'href', '/data/story/story.mp4'
    )
    page.evaluate(
        """
        () => {
            const video = document.querySelector('.video.html5 video');
            if (video) {
                video.removeAttribute('controls');
            }
        }
        """
    )
    vrt.screenshot(page.locator('#story'), 'story-album.png')
