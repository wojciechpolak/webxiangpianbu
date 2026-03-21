"""
#  WebXiangpianbu Copyright (C) 2026 Wojciech Polak
#
#  This program is free software; you can redistribute it and/or modify it
#  under the terms of the GNU General Public License as published by the Free
#  Software Foundation; either version 3 of the License, or (at your option)
#  any later version.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
#  FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
#  more details.
#
#  You should have received a copy of the GNU General Public License along with
#  this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse

import pytest
from PIL import Image, ImageChops
from playwright.sync_api import Locator, Page


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE_ROOT = PROJECT_ROOT / '.visual-regression'
ARTIFACT_ROOT = PROJECT_ROOT / 'test-results' / 'vrt'
CSS_IMPORT_RE = re.compile(
    r'@import url\((?P<quote>[\'"]?)(?P<href>[^\'")]+)(?P=quote)\);?'
)


def _env_flag(name: str) -> bool:
    value = os.environ.get(name, '')
    return value.lower() in {'1', 'true', 'yes', 'on'}


def _slugify(value: str) -> str:
    return re.sub(r'[^A-Za-z0-9_.-]+', '-', value).strip('-') or 'snapshot'


def _snapshot_slug(name: str) -> str:
    return _slugify(Path(name).stem)


def _stylesheet_path_from_href(href: str) -> Path | None:
    parsed = urlparse(href)
    path = parsed.path or href
    if not path:
        return None
    if path.startswith('/'):
        path = path[1:]
    return (PROJECT_ROOT / path).resolve()


def _expand_css_file(path: Path, seen: set[Path]) -> str:
    resolved = path.resolve()
    if resolved in seen or not resolved.exists():
        return ''
    seen.add(resolved)

    text = resolved.read_text(encoding='utf-8')
    chunks: list[str] = []
    for match in CSS_IMPORT_RE.finditer(text):
        imported = (resolved.parent / match.group('href')).resolve()
        chunks.append(_expand_css_file(imported, seen))

    chunks.append(CSS_IMPORT_RE.sub('', text))
    return '\n'.join(chunk for chunk in chunks if chunk.strip())


def _screenshot_style(page: Page) -> str | None:
    hrefs = page.locator('link[rel="stylesheet"]').evaluate_all(
        '(links) => links.map((link) => link.getAttribute("href") || "")'
    )
    seen: set[Path] = set()
    css_chunks: list[str] = []
    for href in hrefs:
        css_path = _stylesheet_path_from_href(href)
        if css_path is None:
            continue
        css = _expand_css_file(css_path, seen)
        if css:
            css_chunks.append(css)
    if not css_chunks:
        return None
    return '\n'.join(css_chunks)


def _load_image_bytes(data: bytes) -> Image.Image:
    with Image.open(BytesIO(data)) as image:
        return image.convert('RGB')


def _load_image_file(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return image.convert('RGB')


def _prepare_page_for_screenshot(page: Page) -> None:
    page.wait_for_load_state('networkidle')
    page.evaluate(
        """
        () => {
            if (document.fonts && document.fonts.ready) {
                return document.fonts.ready;
            }
            return null;
        }
        """
    )
    page.wait_for_function(
        """
        () => {
            const stylesheets = Array.from(
                document.querySelectorAll('link[rel="stylesheet"]')
            );
            return stylesheets.every((link) => link.sheet);
        }
        """
    )
    page.wait_for_function(
        """
        () => {
            const images = Array.from(document.querySelectorAll('img'));
            return images.every(
                (img) =>
                    img.complete &&
                    typeof img.naturalWidth === 'number' &&
                    img.naturalWidth > 0
            );
        }
        """
    )
    page.wait_for_function(
        """
        () => {
            const dialogs = Array.from(document.querySelectorAll('.dialog'));
            return dialogs.every((dialog) => {
                const style = window.getComputedStyle(dialog);
                return style.display === 'none' || style.opacity === '1';
            });
        }
        """
    )
    page.wait_for_function(
        """
        () => {
            if (typeof window.jQuery === 'undefined') {
                return true;
            }
            return window.jQuery(':animated').length === 0;
        }
        """
    )
    page.evaluate(
        """
        () => {
            const active = document.activeElement;
            if (active && typeof active.blur === 'function') {
                active.blur();
            }
        }
        """
    )


def _screenshot_locator(
    target: Locator,
    *,
    mask: list[Locator] | None,
    style: str | None,
) -> bytes:
    page = target.page
    _prepare_page_for_screenshot(page)
    screenshot_style = _screenshot_style(page)
    if screenshot_style and style:
        style = f'{screenshot_style}\n{style}'
    elif screenshot_style:
        style = screenshot_style
    image_bytes = page.screenshot(
        full_page=True,
        animations='disabled',
        caret='hide',
        scale='css',
        mask=mask,
        style=style,
    )
    box = target.bounding_box()
    if box is None:
        return image_bytes

    left = int(box['x'])
    top = int(box['y'])
    right = int(box['x'] + box['width'] + 0.999999)
    bottom = int(box['y'] + box['height'] + 0.999999)
    with Image.open(BytesIO(image_bytes)) as image:
        cropped = image.crop((left, top, right, bottom)).convert('RGB')
        buffer = BytesIO()
        cropped.save(buffer, format='PNG')
        return buffer.getvalue()


@dataclass(frozen=True)
class VisualRegressionSession:
    root: Path
    enabled: bool
    update: bool
    dump: bool

    @classmethod
    def from_request(cls, request: pytest.FixtureRequest) -> VisualRegressionSession:
        relative_file = (
            request.node.path.resolve().relative_to(PROJECT_ROOT).with_suffix('')
        )
        root = relative_file / _slugify(request.node.name)
        return cls(
            root=root,
            enabled=_env_flag('VRT'),
            update=_env_flag('VRT_UPDATE') or _env_flag('VRT_BASELINE'),
            dump=_env_flag('VRT_DUMP'),
        )

    def baseline_path(self, name: str) -> Path:
        return BASELINE_ROOT / self.root / f'{_snapshot_slug(name)}.png'

    def artifact_dir(self, name: str) -> Path:
        return ARTIFACT_ROOT / self.root / _snapshot_slug(name)

    def screenshot(
        self,
        target: Page | Locator,
        name: str,
        *,
        full_page: bool = False,
        mask: Sequence[Locator] = (),
        style: str | None = None,
    ) -> None:
        if not self.enabled:
            return

        mask_list = list(mask) if mask else None
        if isinstance(target, Page):
            _prepare_page_for_screenshot(target)
            screenshot_style = _screenshot_style(target)
            if screenshot_style and style:
                style = f'{screenshot_style}\n{style}'
            elif screenshot_style:
                style = screenshot_style
            image_bytes = target.screenshot(
                full_page=full_page,
                animations='disabled',
                caret='hide',
                scale='css',
                mask=mask_list,
                style=style,
            )
        else:
            image_bytes = _screenshot_locator(
                target,
                mask=mask_list,
                style=style,
            )
        self._compare_snapshot(name, image_bytes)

    def screenshot_locator(
        self,
        target: Locator,
        name: str,
        *,
        mask: Sequence[Locator] = (),
        style: str | None = None,
    ) -> None:
        if not self.enabled:
            return

        page = target.page
        _prepare_page_for_screenshot(page)
        screenshot_style = _screenshot_style(page)
        if screenshot_style and style:
            style = f'{screenshot_style}\n{style}'
        elif screenshot_style:
            style = screenshot_style
        image_bytes = target.screenshot(
            animations='disabled',
            caret='hide',
            scale='css',
            mask=list(mask) if mask else None,
            style=style,
        )
        self._compare_snapshot(name, image_bytes)

    def _compare_snapshot(self, name: str, image_bytes: bytes) -> None:
        baseline_path = self.baseline_path(name)

        if self.update:
            baseline_path.parent.mkdir(parents=True, exist_ok=True)
            baseline_path.write_bytes(image_bytes)
            return

        if not baseline_path.exists():
            actual = _load_image_bytes(image_bytes)
            self._write_artifacts(
                name,
                actual=actual,
                expected=actual,
                mismatch_note='Baseline image is missing.',
            )
            raise AssertionError(self._failure_message(name, baseline_path))

        expected = _load_image_file(baseline_path)
        actual = _load_image_bytes(image_bytes)
        if expected.size != actual.size:
            self._write_artifacts(
                name,
                actual=actual,
                expected=expected,
                mismatch_note=(
                    f'Image sizes differ: expected {expected.size}, actual {actual.size}.'
                ),
            )
            raise AssertionError(self._failure_message(name, baseline_path))

        diff = ImageChops.difference(expected, actual)
        if diff.getbbox() is not None:
            self._write_artifacts(name, actual=actual, expected=expected, diff=diff)
            raise AssertionError(self._failure_message(name, baseline_path))

        if self.dump:
            self._write_artifacts(
                name,
                actual=actual,
                expected=expected,
                mismatch_note='Compare dump requested.',
            )

    def _write_artifacts(
        self,
        name: str,
        *,
        actual: Image.Image,
        expected: Image.Image,
        diff: Image.Image | None = None,
        mismatch_note: str | None = None,
    ) -> None:
        artifact_dir = self.artifact_dir(name)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        actual.save(artifact_dir / 'actual.png')
        expected.save(artifact_dir / 'expected.png')
        if diff is not None:
            diff.save(artifact_dir / 'diff.png')
        if mismatch_note is not None:
            (artifact_dir / 'note.txt').write_text(
                f'{mismatch_note}\n', encoding='utf-8'
            )

    def _failure_message(self, name: str, baseline_path: Path) -> str:
        artifact_dir = self.artifact_dir(name)
        compare_mode = 'VRT=1 VRT_UPDATE=1' if self.update else 'VRT=1'
        return (
            f'Visual regression mismatch for {self.root.as_posix()}/'
            f'{_snapshot_slug(name)}.\n'
            f'Baseline: {baseline_path}\n'
            f'Artifacts: {artifact_dir}\n'
            f'Run {compare_mode} uv run pytest -m e2e to refresh baselines.'
        )
