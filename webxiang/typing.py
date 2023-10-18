"""
#  WebXiangpianbu Copyright (C) 2023 Wojciech Polak
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

from typing import TypedDict, Any

from django.core.paginator import Paginator


class MetaData(TypedDict, total=False):
    columns: int
    copyright: str
    cover: str | None
    custom_menu: bool
    default_image_size: tuple[int, int]
    default_thumb_size: tuple[int, int]
    description: str
    path: str
    path_thumb: str
    ppp: int
    reverse_order: bool
    robots: str
    style: str
    template: str
    thumbs_skip: bool
    title: str
    title_gallery: str


class Image(TypedDict, total=False):
    file: str
    path: str
    size: tuple[int, int]


class Entry(TypedDict, total=False):
    album: str
    copyright: str
    description: str
    exif: dict
    geo: tuple[float, float]
    image: Image
    index: int
    link: str
    poster: str | bool
    size: tuple[int, int]
    slug: str
    thumb: str
    type: str
    url: str
    url_full: str
    vid: str
    video: str


class Album(TypedDict, total=False):
    album: str
    canonical_url: str
    entries: list[Entry] | Paginator
    entry: Entry
    groups: Any
    meta: MetaData
    mode: str
    next_entry: str | None
    prev_entry: str | None
    settings: dict
    STATIC_URL: str
    URL_PHOTOS: str
    wxpb_settings: str
