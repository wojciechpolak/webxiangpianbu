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
from pathlib import Path

from PIL import Image

from tools import convert, generate


def _make_image(path: Path, size: tuple[int, int], color: str = 'blue') -> None:
    image = Image.new('RGB', size, color=color)
    image.save(path, format='JPEG')


def test_generate_geo_helpers_round_and_flip_coordinates():
    assert generate._geo_convert_to_degress((50, 30, 0)) == 50.5
    assert generate.get_latlng(
        {
            'GPSLatitude': (50, 30, 0),
            'GPSLatitudeRef': 'N',
            'GPSLongitude': (19, 30, 0),
            'GPSLongitudeRef': 'E',
        }
    ) == (50.5, 19.5)
    assert generate.get_latlng(
        {
            'GPSLatitude': (50, 30, 0),
            'GPSLatitudeRef': 'S',
            'GPSLongitude': (19, 30, 0),
            'GPSLongitudeRef': 'W',
        }
    ) == (-50.5, -19.5)


def test_generate_get_latlng_returns_none_without_complete_gps_data():
    assert generate.get_latlng({}) == (None, None)


def test_generate_gen_thumbnails_creates_center_crop(tmp_path):
    source = tmp_path / 'source.jpg'
    output_dir = tmp_path / 'out'
    output_dir.mkdir()
    _make_image(source, (400, 200))

    img = Image.open(source)
    thumb_name = generate.gen_thumbnails(
        {
            'outputdir': str(output_dir),
            'thumbs_size': (180, 180),
            'skip_thumb_gen': False,
            'images_format': 'JPEG',
            'thumbs_quality': 90,
        },
        img,
        'source.jpg',
    )

    assert thumb_name == 'source-180x180.jpg'
    thumb = Image.open(output_dir / thumb_name)
    assert thumb.size == (180, 180)


def test_generate_process_image_writes_rotated_output(tmp_path, monkeypatch):
    source_dir = tmp_path / 'input'
    output_dir = tmp_path / 'out'
    source_dir.mkdir()
    output_dir.mkdir()
    source = source_dir / 'portrait.jpg'
    _make_image(source, (100, 200))
    rotations: list[int] = []
    real_source = Image.open(source)

    class FakeImage:
        mode = 'RGB'
        size = (100, 200)

        def __init__(self):
            self._real = real_source

        def convert(self, mode):
            return self

        def _getexif(self):
            return {
                274: 6,
                34853: {
                    1: 'N',
                    2: (50, 30, 0),
                    3: 'E',
                    4: (19, 30, 0),
                },
                36867: '2024:01:02 03:04:05',
            }

        def rotate(self, angle):
            rotations.append(angle)
            return self

        def thumbnail(self, size, resample):
            return None

        def save(self, output_fname, *args, **kwargs):
            self._real.save(output_fname, format='JPEG')

    monkeypatch.setattr(generate.Image, 'open', lambda path: FakeImage())

    album = {'meta': {'default_image_size': []}, 'entries': []}
    opts = {
        'inputdir': str(source_dir),
        'outputdir': str(output_dir),
        'idx': 1,
        'images_format': 'JPEG',
        'images_quality': 95,
        'images_maxsize': (1000, 1000),
        'images_sharpness': 0,
        'thumbs_skip': True,
        'skip_image_gen': False,
        'correct_orientation': True,
    }

    generate.process_image(opts, album, 'portrait.jpg')

    output = Image.open(output_dir / 'portrait.jpg')
    assert rotations == [270]
    assert output.size == (100, 200)
    assert album['entries'][0]['image']['size'] == [100, 200]
    assert album['entries'][0]['geo'] == '50.5,19.5'
    assert album['entries'][0]['exif']['DateTimeOriginal'] == '2024:01:02 03:04:05'


def test_generate_confirm_handles_empty_yes_and_no(monkeypatch):
    answers = iter(['', 'y', 'no'])
    monkeypatch.setattr('builtins.input', lambda prompt: next(answers))

    assert generate.confirm('question', default=True) is True
    assert generate.confirm('question') is True
    assert generate.confirm('question') is False


def test_convert_read_albumfile_handles_json_and_yaml(tmp_path):
    json_path = tmp_path / 'album.json'
    yaml_path = tmp_path / 'album.yaml'
    json_path.write_text(
        json.dumps({'meta': {'title': 'json'}, 'entries': []}), encoding='utf-8'
    )
    yaml_path.write_text('meta:\n  title: yaml\nentries: []\n', encoding='utf-8')

    json_data = convert.read_albumfile(str(json_path))
    yaml_data = convert.read_albumfile(str(yaml_path))

    assert json_data is not None
    assert yaml_data is not None
    assert json_data['meta']['title'] == 'json'
    assert yaml_data['meta']['title'] == 'yaml'
    assert convert.read_albumfile(str(tmp_path / 'missing.json')) is None


def test_convert_to_json_and_yaml_write_files(tmp_path):
    data = {'meta': {'title': 'Album'}, 'entries': [{'image': 'one.jpg'}]}
    opts = {'output_dir': str(tmp_path), 'output_name': '', 'overwrite': True}

    convert.to_json(opts, str(tmp_path / 'album.yaml'), data)
    convert.to_yaml(opts, str(tmp_path / 'album.json'), data)

    assert json.loads((tmp_path / 'album.json').read_text(encoding='utf-8')) == data
    assert convert.read_albumfile(str(tmp_path / 'album.yaml')) == data


def test_convert_confirm_handles_yes_no_and_default(monkeypatch):
    answers = iter(['', 'yes', 'n'])
    monkeypatch.setattr('builtins.input', lambda prompt: next(answers))

    assert convert.confirm('question', default=False) is False
    assert convert.confirm('question') is True
    assert convert.confirm('question') is False
