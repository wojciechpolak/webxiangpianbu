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
from datetime import date
from pathlib import Path
from typing import Any

import pytest

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

    album: dict[str, Any] = {'meta': {'default_image_size': []}, 'entries': []}
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


def test_generate_parse_args_converts_option_values():
    opts = generate.default_opts()
    generate.parse_args(
        opts,
        [
            '--album-name=trip',
            '--album-format=JSON',
            '--ppp=7',
            '--show-geo=0',
            '--correct-orientation=0',
            '--images-quality=80',
            '--images-sharpness=1.5',
            '--images-maxsize=640x480',
            '--images-default-size=640x427',
            '--thumbs-skip',
            '--thumbs-size=90x60',
            '--skip-image-gen',
            '--skip-thumb-gen',
            'in',
            'out',
        ],
    )

    assert opts['album_name'] == 'trip'
    assert opts['album_format'] == 'json'
    assert opts['ppp'] == 7
    assert opts['show_geo'] is False
    assert opts['correct_orientation'] is False
    assert opts['images_quality'] == 80
    assert opts['images_sharpness'] == 1.5
    assert opts['images_maxsize'] == [640, 480]
    assert opts['default_image_size'] == [640, 427]
    assert opts['thumbs_skip'] is True
    assert opts['thumbs_size'] == (90, 60)
    assert opts['skip_image_gen'] is True
    assert opts['skip_thumb_gen'] is True
    assert (opts['inputdir'], opts['outputdir']) == ('in', 'out')


@pytest.mark.parametrize('argv', [['--help', 'in', 'out'], ['in'], []])
def test_generate_main_prints_usage_on_bad_arguments(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        generate.main(argv)

    assert exc.value.code == 1
    assert '--album-format=STRING' in capsys.readouterr().out


def test_generate_new_album_takes_meta_from_options():
    opts = generate.default_opts()
    opts.update(template='story', copyright='Me', default_image_size=[4, 3])

    album = generate.new_album(opts)

    assert album['entries'] == []
    assert album['meta']['thumbs_skip'] is True
    assert album['meta']['copyright'] == 'Me'
    assert album['meta']['default_image_size'] == [4, 3]

    album = generate.new_album(generate.default_opts())
    assert album['meta']['thumbs_skip'] is False
    assert album['meta']['copyright'] == str(date.today().year)
    assert album['meta']['default_image_size'] == []


def test_generate_list_input_files_reads_a_list_file(tmp_path):
    (tmp_path / 'b.jpg').touch()
    (tmp_path / 'a.jpg').touch()
    list_file = tmp_path / 'photos.in'
    list_file.write_text(
        f'{tmp_path}\nb.jpg  # the best one\n\n# skipped\na.jpg\n', encoding='utf-8'
    )

    opts = {'inputdir': str(tmp_path)}
    assert generate.list_input_files(opts) == ['a.jpg', 'b.jpg', 'photos.in']

    opts = {'inputdir': str(list_file)}
    assert generate.list_input_files(opts) == ['b.jpg', 'a.jpg']
    assert opts['inputdir'] == str(tmp_path)


def test_generate_parse_exif_formats_tags_and_collects_gps():
    exif_data, gps_data, orientation = generate.parse_exif(
        {
            271: 'Maker',  # Make
            274: 6,  # Orientation
            33434: 0.004,  # ExposureTime
            33437: 2.8,  # FNumber
            34853: {1: 'N', 2: (50, 30, 0)},  # GPSInfo
            99999: 'unknown',
        }
    )

    assert exif_data == {
        'Make': 'Maker',
        'ExposureTime': '1/250 sec',
        'FNumber': 'f/2.8',
    }
    assert gps_data == {'GPSLatitudeRef': 'N', 'GPSLatitude': (50, 30, 0)}
    assert orientation == 6
    assert generate.parse_exif(None) == ({}, {}, None)


def test_generate_read_exif_tolerates_missing_or_broken_exif():
    class Broken:
        def _getexif(self):
            raise ValueError('corrupt')

    assert generate.read_exif(object()) is None
    assert generate.read_exif(Broken()) is None


def _generate_opts(source_dir: Path, output_dir: Path, **kwargs) -> dict:
    opts = generate.default_opts()
    opts.update(inputdir=str(source_dir), outputdir=str(output_dir), idx=1)
    opts.update(kwargs)
    return opts


def test_generate_process_image_converts_and_skips_existing_output(tmp_path):
    source_dir = tmp_path / 'in'
    output_dir = tmp_path / 'out'
    source_dir.mkdir()
    output_dir.mkdir()
    Image.new('L', (400, 300)).save(source_dir / 'Gray.JPEG', format='JPEG')
    album: dict[str, Any] = {'meta': {'default_image_size': []}, 'entries': []}

    opts = _generate_opts(source_dir, output_dir, images_format='WEBP')
    generate.process_image(opts, album, 'Gray.JPEG')

    entry = album['entries'][0]
    assert entry['image'] == {'file': 'Gray.webp', 'size': [400, 300]}
    assert entry['thumb'] == 'Gray-180x180.webp'
    assert 'exif' not in entry
    assert Image.open(output_dir / 'Gray.webp').mode == 'RGB'

    # a second run leaves the existing file alone
    (output_dir / 'Gray.webp').write_bytes(b'kept')
    generate.process_image(opts, album, 'Gray.JPEG')
    assert (output_dir / 'Gray.webp').read_bytes() == b'kept'


def test_generate_process_image_can_skip_image_generation(tmp_path):
    source_dir = tmp_path / 'in'
    output_dir = tmp_path / 'out'
    source_dir.mkdir()
    output_dir.mkdir()
    _make_image(source_dir / 'a.jpg', (90, 60))
    album: dict[str, Any] = {'meta': {'default_image_size': [90, 60]}, 'entries': []}

    opts = _generate_opts(
        source_dir,
        output_dir,
        skip_image_gen=True,
        skip_thumb_gen=True,
        images_sharpness=0,
    )
    generate.process_image(opts, album, 'a.jpg')

    assert album['entries'][0]['image'] == 'a.jpg'
    assert list(output_dir.iterdir()) == []


def test_generate_main_writes_json_and_yaml_albums(tmp_path, monkeypatch, capsys):
    source_dir = tmp_path / 'in'
    output_dir = tmp_path / 'trip'
    source_dir.mkdir()
    _make_image(source_dir / 'b.jpg', (400, 300))
    _make_image(source_dir / 'a.JPG', (300, 400))
    (source_dir / 'notes.txt').write_text('not a photo', encoding='utf-8')

    generate.main(['--album-format=all', str(source_dir), str(output_dir)])

    album = json.loads((output_dir / 'trip.json').read_text(encoding='utf-8'))
    assert [entry['idx'] for entry in album['entries']] == [1, 2]
    assert [entry['image']['file'] for entry in album['entries']] == [
        'a.jpg',
        'b.jpg',
    ]
    yaml_text = (output_dir / 'trip.yaml').read_text(encoding='utf-8')
    assert yaml_text.startswith('meta:')
    assert convert.read_albumfile(str(output_dir / 'trip.yaml')) == album
    assert capsys.readouterr().out.endswith('done\n')

    # existing album files are only replaced after confirmation
    monkeypatch.setattr('builtins.input', lambda prompt: 'n')
    (output_dir / 'trip.json').write_text('{}', encoding='utf-8')
    generate.main(['--album-format=json', str(source_dir), str(output_dir)])
    assert (output_dir / 'trip.json').read_text(encoding='utf-8') == '{}'

    monkeypatch.setattr('builtins.input', lambda prompt: 'y')
    generate.main(
        [
            '--album-name=renamed',
            f'--album-dir={tmp_path}',
            str(source_dir),
            f'{tmp_path}/other/',
        ]
    )
    assert (tmp_path / 'renamed.yaml').exists()


def test_convert_parse_args_collects_inputs_and_output(tmp_path):
    (tmp_path / 'one.json').touch()
    (tmp_path / 'two.json').touch()
    opts: dict[str, Any] = {'overwrite': False, 'output_dir': '', 'output_name': ''}

    convert.parse_args(opts, ['-y', str(tmp_path / '*.json'), 'out/album.yaml'])

    assert opts['overwrite'] is True
    assert sorted(opts['input']) == [
        str(tmp_path / 'one.json'),
        str(tmp_path / 'two.json'),
    ]
    assert opts['output_dir'] == 'out'
    assert opts['output_name'] == 'album.yaml'


def test_convert_main_prints_usage_without_input(capsys):
    with pytest.raises(SystemExit) as exc:
        convert.main([])

    assert exc.value.code == 1
    assert '--overwrite' in capsys.readouterr().out


def test_convert_main_converts_both_ways(tmp_path, capsys):
    data = {'meta': {'title': 'Album'}, 'entries': [{'image': 'one.jpg'}]}
    (tmp_path / 'a.json').write_text(json.dumps(data), encoding='utf-8')
    (tmp_path / 'b.yaml').write_text('meta:\n  title: B\n', encoding='utf-8')
    (tmp_path / 'broken.json').write_text('{', encoding='utf-8')
    out_dir = tmp_path / 'out'

    convert.main([str(tmp_path / 'a.json'), str(out_dir / 'a.yaml')])
    convert.main([str(tmp_path / 'b.yaml')])
    convert.main([str(tmp_path / 'broken.json')])

    assert convert.read_albumfile(str(out_dir / 'a.yaml')) == data
    assert json.loads((tmp_path / 'b.json').read_text(encoding='utf-8')) == {
        'meta': {'title': 'B'}
    }
    assert not (tmp_path / 'broken.yaml').exists()
    assert 'done' in capsys.readouterr().out


def test_convert_file_ignores_other_extensions(tmp_path, monkeypatch):
    monkeypatch.setattr(convert, 'read_albumfile', lambda name: {'meta': {}})
    opts = {'overwrite': True, 'output_dir': str(tmp_path), 'output_name': ''}

    convert.convert_file(opts, 'album.txt')

    assert list(tmp_path.iterdir()) == []


def test_convert_asks_before_overwriting(tmp_path, monkeypatch):
    for target in (tmp_path / 'album.json', tmp_path / 'album.yaml'):
        target.write_text('{}', encoding='utf-8')
    monkeypatch.setattr('builtins.input', lambda prompt: 'n')
    opts: dict[str, Any] = {'overwrite': False, 'output_dir': '', 'output_name': ''}

    convert.to_json(opts, str(tmp_path / 'album.yaml'), {'meta': {}})
    convert.to_yaml(opts, str(tmp_path / 'album.json'), {'meta': {}})

    assert (tmp_path / 'album.json').read_text(encoding='utf-8') == '{}'
    assert (tmp_path / 'album.yaml').read_text(encoding='utf-8') == '{}'
