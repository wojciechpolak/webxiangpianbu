#!/usr/bin/env python3
#
"""
#  WebXiangpianbu Copyright (C) 2013, 2014, 2015, 2023 Wojciech Polak
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

import argparse
import json
import logging
import os
import sys
from collections import OrderedDict as _OrderedDict
from datetime import datetime
from typing import Any

import yaml
from PIL import ExifTags, Image, ImageEnhance, ImageFile

OrderedDict: Any = _OrderedDict


logger = logging.getLogger('tools.generate')


def default_opts() -> dict[str, Any]:
    return {
        'album_name': None,
        'album_dir': None,
        'album_format': 'yaml',
        'path': '',
        'copyright': '',
        'template': 'default',
        'style': 'base.css',
        'ppp': 12,  # pictures per page
        'images_format': 'JPEG',
        'images_quality': 95,
        'images_maxsize': [900, 640],
        'images_sharpness': 1.4,
        'default_image_size': [],
        'thumbs_skip': False,
        'thumbs_quality': 90,
        'thumbs_size': [180, 180],
        'show_geo': True,
        'correct_orientation': True,
        'skip_image_gen': False,
        'skip_thumb_gen': False,
    }


def _size(arg: str) -> list[int]:
    """'WxH' as [W, H]."""
    try:
        width, height = arg.split('x')
        return [int(width), int(height)]
    except ValueError:
        raise argparse.ArgumentTypeError(f'expected WxH, got {arg!r}') from None


def _flag(arg: str) -> bool:
    """'0' or '1' as a bool."""
    if arg not in ('0', '1'):
        raise argparse.ArgumentTypeError(f'expected 0 or 1, got {arg!r}')
    return arg == '1'


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Generate an album file, images and thumbnails '
        'from a directory of JPEG photos.'
    )
    parser.add_argument(
        'inputdir',
        metavar='INPUT-DIR',
        help='photo directory, or a .in list file whose first line names '
        'the directory and the other lines the photos',
    )
    parser.add_argument(
        'outputdir', metavar='OUTPUT-DIR', help='where images and thumbnails go'
    )
    parser.add_argument(
        '--album-name', metavar='NAME', help="default: OUTPUT-DIR's name"
    )
    parser.add_argument('--album-dir', metavar='DIR', help='default: OUTPUT-DIR')
    parser.add_argument(
        '--album-format',
        type=str.lower,
        choices=('yaml', 'json', 'all'),
        help='default: %(default)s',
    )
    parser.add_argument('--path', help='meta.path, default: empty')
    parser.add_argument('--copyright', help='meta.copyright, default: the year')
    parser.add_argument(
        '--template',
        help='meta.template (default, floating, story, ...), default: %(default)s',
    )
    parser.add_argument('--style', help='meta.style, default: %(default)s')
    parser.add_argument(
        '--ppp', type=int, metavar='N', help='pictures per page, default: %(default)s'
    )
    parser.add_argument(
        '--images-format',
        type=str.upper,
        choices=('JPEG', 'WEBP'),
        help='default: %(default)s',
    )
    parser.add_argument(
        '--images-quality', type=int, metavar='0..100', help='default: %(default)s'
    )
    parser.add_argument(
        '--images-sharpness', type=float, metavar='FACTOR', help='default: %(default)s'
    )
    parser.add_argument(
        '--images-maxsize', type=_size, metavar='WxH', help='default: 900x640'
    )
    parser.add_argument(
        '--images-default-size',
        dest='default_image_size',
        type=_size,
        metavar='WxH',
        help='meta.default_image_size, default: none',
    )
    parser.add_argument(
        '--thumbs-skip', action='store_true', help='album without thumbnails'
    )
    parser.add_argument(
        '--thumbs-quality', type=int, metavar='0..100', help='default: %(default)s'
    )
    parser.add_argument(
        '--thumbs-size', type=_size, metavar='WxH', help='default: 180x180'
    )
    parser.add_argument(
        '--show-geo', type=_flag, metavar='0|1', help='meta.geo, default: 1'
    )
    parser.add_argument(
        '--correct-orientation',
        type=_flag,
        metavar='0|1',
        help='rotate images upright using EXIF, default: 1',
    )
    parser.add_argument(
        '--skip-image-gen', action='store_true', help='do not write images'
    )
    parser.add_argument(
        '--skip-thumb-gen', action='store_true', help='do not write thumbnails'
    )
    parser.set_defaults(**default_opts())
    return parser


def parse_args(argv: list[str]) -> dict[str, Any]:
    return vars(build_parser().parse_args(argv))


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(format='%(levelname)s: %(message)s')
    opts = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        fnames = list_input_files(opts)
    except OSError as exc:
        logger.error('cannot read %s: %s', opts['inputdir'], exc)
        sys.exit(1)

    os.makedirs(opts['outputdir'], exist_ok=True)
    album = new_album(opts)
    failed = add_images(opts, album, fnames)
    write_album(opts, album)
    if failed:
        sys.exit(1)
    print('done')


def add_images(opts: dict[str, Any], album: dict[str, Any], fnames: list[str]) -> int:
    """Add the JPEG files among `fnames` to `album`. The number that failed."""
    failed = 0
    for fname in fnames:
        if not fname.lower().endswith(('.jpg', '.jpeg')):
            continue
        opts['idx'] = len(album['entries']) + 1
        try:
            process_image(opts, album, fname)
        except OSError as exc:
            logger.error('skipping %s: %s', fname, exc)
            failed += 1
    return failed


def write_album(opts: dict[str, Any], album: dict[str, Any]) -> None:
    album_name = (
        opts['album_name'] or os.path.basename(opts['outputdir'].rstrip('/')) or 'foo'
    )
    album_dir = opts['album_dir'] or opts['outputdir']

    if opts['album_format'] in ('json', 'all'):
        write_json(os.path.normpath(f'{album_dir}/{album_name}.json'), album)
    if opts['album_format'] in ('yaml', 'all'):
        write_yaml(os.path.normpath(f'{album_dir}/{album_name}.yaml'), album)


def new_album(opts: dict[str, Any]) -> dict[str, Any]:
    """An album with no entries yet, its meta taken from the options."""
    meta = {
        'path': opts['path'],
        'title': '',
        'ppp': opts['ppp'],
        'columns': 4,
        'template': opts['template'],
        'thumbs_skip': opts['thumbs_skip'] or opts['template'] == 'story',
        'style': opts['style'],
        'copyright': opts['copyright'] or f'{datetime.now().astimezone().year}',
        'geo': opts['show_geo'],
        'default_image_size': opts['default_image_size'],
        'default_thumb_size': opts['thumbs_size'],
    }
    return {'meta': meta, 'entries': []}


def list_input_files(opts: dict[str, Any]) -> list[str]:
    """Files in the input directory, sorted. An input ending in `.in` is a
    list file instead: its first line names the directory, the other lines
    the files (`#` starts a comment). `opts['inputdir']` is updated then."""
    if not opts['inputdir'].endswith('.in'):
        return sorted(os.listdir(opts['inputdir']))

    with open(opts['inputdir'], encoding='utf-8') as fp:
        data = fp.readlines()
    opts['inputdir'] = data[0].strip()  # first line points directory
    files = (line.split('#')[0].strip() for line in data[1:])
    return [line for line in files if line]


def _may_write(filename: str) -> bool:
    return not os.path.exists(filename) or confirm(f'Overwrite album file {filename}?')


def write_json(filename: str, album: dict[str, Any]) -> None:
    if not _may_write(filename):
        return
    with open(filename, 'w', encoding='utf-8') as album_file_json:
        json.dump(album, album_file_json, indent=4)
        album_file_json.write('\n')
        print(f'saved {album_file_json.name}')


def _represent_ordered(dumper: yaml.Dumper, data: dict[str, Any]) -> yaml.Node:
    return dumper.represent_mapping(
        'tag:yaml.org,2002:map', list(data.items()), flow_style=False
    )


def write_yaml(filename: str, album: dict[str, Any]) -> None:
    if not _may_write(filename):
        return
    yaml.add_representer(OrderedDict, _represent_ordered)
    ordered = OrderedDict({'meta': album['meta'], 'entries': album['entries']})
    with open(filename, 'w', encoding='utf-8') as album_file_yaml:
        yaml.dump(
            ordered,
            album_file_yaml,
            encoding='utf-8',
            default_flow_style=None,
            indent=4,
            width=70,
        )
        print(f'saved {album_file_yaml.name}')


exif_tags = {
    'ApertureValue': lambda v: f'f/{float(v)}',
    'DateTimeOriginal': lambda v: v,
    'ExposureBiasValue': lambda v: f'{v} EV',
    'ExposureTime': lambda v: f'1/{int(1 / float(v))} sec',
    'FNumber': lambda v: f'f/{float(v)}',
    'FocalLength': lambda v: f'{float(v)}mm',
    'ISOSpeedRatings': lambda v: v,
    'LensMake': lambda v: v,
    'LensModel': lambda v: v,
    'Make': lambda v: v,
    'Model': lambda v: v,
}

# EXIF Orientation value -> rotation that makes the image upright
ORIENTATION_ROTATION = {3: 180, 6: 270, 8: 90}


def process_image(opts: dict[str, Any], album: dict[str, Any], fname: str) -> None:
    img: Any = Image.open(os.path.join(opts['inputdir'], fname))

    # lower case for file suffix
    fn = fname.split('.')
    suffix = 'webp' if opts['images_format'] == 'WEBP' else 'jpg'
    fname = f'{"".join(fn[0:-1])}.{suffix}'

    data = OrderedDict()
    data['idx'] = opts['idx']
    data['image'] = fname

    if img.mode != 'RGB':
        img = img.convert('RGB')

    if not opts['thumbs_skip']:
        data['thumb'] = gen_thumbnails(opts, img, fname)

    exif_data, gps_data, orientation = parse_exif(read_exif(img))
    if opts['correct_orientation'] and orientation in ORIENTATION_ROTATION:
        img = img.rotate(ORIENTATION_ROTATION[orientation])

    lat, lng = get_latlng(gps_data)
    if lat and lng:
        data['geo'] = f'{lat},{lng}'

    if exif_data:
        data['exif'] = exif_data

    album['entries'].append(data)

    resample = Image.Resampling.LANCZOS
    img.thumbnail(opts['images_maxsize'], resample)
    if list(img.size) != album['meta']['default_image_size']:
        data['image'] = {'file': fname, 'size': list(img.size)}

    output_fname = os.path.join(opts['outputdir'], fname)
    if os.path.exists(output_fname):
        print(f'file exists, skipping... {output_fname}')
        return

    if not opts['skip_image_gen']:
        save_image(opts, img, output_fname)


def read_exif(img: Any) -> dict[int, Any] | None:
    try:
        exif_getter = getattr(img, '_getexif', None)
        return exif_getter() if exif_getter else None
    except Exception:  # noqa: BLE001 - Pillow raises many types on corrupt EXIF
        return None


def parse_exif(
    exif: dict[int, Any] | None,
) -> tuple[dict[str, str], dict[str, Any], Any]:
    """The accepted EXIF tags formatted for display, the GPS tags, and the
    Orientation value."""
    exif_data: dict[str, str] = {}
    gps_data: dict[str, Any] = {}
    orientation = None
    for tag, value in (exif or {}).items():
        decoded = ExifTags.TAGS.get(tag, str(tag))
        if decoded in exif_tags:
            exif_data[decoded] = str(exif_tags[decoded](value)).strip()
        elif decoded == 'Orientation':
            orientation = value
        elif decoded == 'GPSInfo':
            for t in value:
                gps_data[ExifTags.GPSTAGS.get(t, t)] = value[t]
    return exif_data, gps_data, orientation


def save_image(opts: dict[str, Any], img: Any, output_fname: str) -> None:
    if opts['images_sharpness']:
        sharpener = ImageEnhance.Sharpness(img)
        img = sharpener.enhance(opts['images_sharpness'])

    setattr(ImageFile, 'MAXBLOCK', img.size[0] * img.size[1])  # noqa: B010 - stubs type it Literal
    img.save(
        output_fname,
        opts['images_format'],
        optimize=True,
        quality=opts['images_quality'],
        progressive=False,
    )

    print(f'saved {output_fname}')


def gen_thumbnails(opts: dict[str, Any], img_blob: Any, fname: str) -> str:
    size = opts['thumbs_size']
    fn = fname.split('.')
    fname = f'{"".join(fn[0:-1])}-{size[0]:d}x{size[1]:d}.{fn[-1]}'

    if opts['skip_thumb_gen']:
        return fname

    output_fname = os.path.join(opts['outputdir'], fname)
    if os.path.exists(output_fname):
        print(f'file exists, skipping... {output_fname}')
        return fname

    img = img_blob.copy()

    width, height = img.size
    if width > height:
        delta = width - height
        left = int(delta / 2)
        upper = 0
        right = height + left
        lower = height
    else:
        delta = height - width
        left = 0
        upper = int(delta / 2)
        right = width
        lower = width + upper

    img = img.crop((left, upper, right, lower))
    resample = Image.Resampling.LANCZOS
    img.thumbnail(size, resample)
    setattr(ImageFile, 'MAXBLOCK', 131072)  # noqa: B010 - stubs type it Literal
    img.save(
        output_fname,
        opts['images_format'],
        optimize=True,
        quality=opts['thumbs_quality'],
        progressive=True,
    )

    print(f'saved {output_fname}')
    return fname


def _geo_convert_to_degress(value: tuple[Any, Any, Any]) -> float:
    d = float(value[0])
    m = float(value[1])
    s = float(value[2])
    return d + (m / 60.0) + (s / 3600.0)


def get_latlng(gps_data: dict[str, Any]) -> tuple[float | None, float | None]:
    lat = None
    lng = None

    gps_latitude = gps_data.get('GPSLatitude')
    gps_latitude_ref = gps_data.get('GPSLatitudeRef')
    gps_longitude = gps_data.get('GPSLongitude')
    gps_longitude_ref = gps_data.get('GPSLongitudeRef')

    if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
        lat = _geo_convert_to_degress(gps_latitude)
        if gps_latitude_ref != 'N':
            lat = 0 - lat

        lng = _geo_convert_to_degress(gps_longitude)
        if gps_longitude_ref != 'E':
            lng = 0 - lng

    if lat and lng:
        return round(lat, 6), round(lng, 6)
    return None, None


def confirm(question: str, default: bool = False) -> bool:
    if default:
        defval = 'Y/n'
    else:
        defval = 'y/N'
    while True:
        res = input(f'{question} [{defval}] ').lower()
        if not res:
            return default
        if res in ('y', 'yes'):
            return True
        if res in ('n', 'no'):
            return False


if __name__ == '__main__':
    main()
