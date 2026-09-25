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
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

AXE_OPTIONS = {
    'runOnly': {
        'type': 'tag',
        'values': [
            'wcag2a',
            'wcag2aa',
            'wcag21a',
            'wcag21aa',
            'wcag22aa',
            'best-practice',
        ],
    },
    'resultTypes': ['violations'],
}


@pytest.mark.parametrize('color_scheme', ['light', 'dark'])
@pytest.mark.parametrize('path', ['/', '/album-one/', '/album-one/1', '/story-album/'])
def test_page_has_no_axe_violations(static_page, live_server, path, color_scheme):
    page = static_page
    page.emulate_media(color_scheme=color_scheme)
    page.goto(f'{live_server.url}{path}', wait_until='networkidle')

    results = Axe().run(page, options=AXE_OPTIONS)

    assert results.violations_count == 0, results.generate_report()


def test_help_dialog_has_no_axe_violations(static_page, live_server):
    page = static_page
    page.goto(f'{live_server.url}/album-one/', wait_until='networkidle')
    page.locator('#show-help').click()
    expect(page.locator('#help')).to_be_visible()
    page.wait_for_function(
        "getComputedStyle(document.getElementById('help')).opacity === '1'"
    )

    results = Axe().run(page, options=AXE_OPTIONS)

    assert results.violations_count == 0, results.generate_report()


def test_keyboard_focus_is_visible(static_page, live_server):
    page = static_page
    page.goto(f'{live_server.url}/album-one/', wait_until='networkidle')

    page.keyboard.press('Tab')
    skip_link = page.locator('.skip-link')
    expect(skip_link).to_be_focused()
    expect(skip_link).to_be_in_viewport()

    page.keyboard.press('Tab')
    expect(page.locator('#levelTop')).to_be_focused()

    page.keyboard.press('Tab')
    thumb = page.locator('a[data-index="1"]')
    expect(thumb).to_be_focused()
    expect(thumb.locator('img')).to_have_css('outline-width', '3px')


def test_help_dialog_keeps_and_restores_focus(static_page, live_server):
    page = static_page
    page.goto(f'{live_server.url}/album-one/', wait_until='networkidle')
    show_help = page.locator('#show-help')

    show_help.focus()
    page.keyboard.press('Enter')
    close = page.locator('#help .close')
    expect(close).to_be_focused()

    # Tab cycles within the dialog
    page.keyboard.press('Tab')
    expect(page.locator('#shortcuts-enabled')).to_be_focused()
    page.keyboard.press('Tab')
    expect(close).to_be_focused()

    page.keyboard.press('Escape')
    expect(page.locator('#help')).to_be_hidden()
    expect(show_help).to_be_focused()


def test_shortcuts_can_be_turned_off(static_page, live_server):
    page = static_page
    page.goto(f'{live_server.url}/album-one/1', wait_until='networkidle')
    page.locator('#show-help').click()
    page.locator('#shortcuts-enabled').uncheck()
    page.keyboard.press('Escape')

    page.keyboard.press('n')
    page.wait_for_timeout(300)
    expect(page).to_have_url(f'{live_server.url}/album-one/1')

    page.locator('#show-help').click()
    page.locator('#shortcuts-enabled').check()
    page.keyboard.press('Escape')
    with page.expect_navigation():
        page.keyboard.press('n')
    expect(page).to_have_url(f'{live_server.url}/album-one/2')
