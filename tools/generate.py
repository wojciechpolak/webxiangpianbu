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

import getopt
import json
import os
import sys
from collections import OrderedDict as _OrderedDict
from collections.abc import Callable
from datetime import datetime
from typing import Any

import yaml
from PIL import ExifTags, Image, ImageEnhance, ImageFile

OrderedDict: Any = _OrderedDict


LONG_OPTIONS = [
    'help',
    'album-name=',
    'album-dir=',
    'album-format=',
    'path=',
    'copyright=',
    'template=',
    'style=',
    'ppp=',
    'images-format=',
    'images-quality=',
    'images-sharpness=',
    'images-maxsize=',
    'images-default-size=',
    'thumbs-skip',
    'thumbs-quality=',
    'thumbs-size=',
    'show-geo=',
    'correct-orientation=',
    'skip-image-gen',
    'skip-thumb-gen',
]

USAGE = """
 Options                      Default values
 --album-name=STRING          [output dir's name]
 --album-dir=STRING           [output dir]
 --album-format=STRING        [%(album_format)s] (yaml|json|all)
 --path=STRING                ['']
 --copyright=STRING           ['']
 --template=STRING            [''] (default|floating|story)
 --style=STRING               ['']
 --ppp=INTEGER                [%(ppp)s]
 --images-format=FORMAT       [%(images_format)s] (JPEG|WEBP)
 --images-quality=INTEGER     [%(images_quality)s] (0..100)
 --images-sharpness=FLOAT     [%(images_sharpness)s]
 --images-maxsize=WxH         [900x640]
 --images-default-size=WxH    [None]
 --thumbs-skip                [%(thumbs_skip)s]
 --thumbs-quality=INTEGER     [%(thumbs_quality)s] (0..100)
 --thumbs-size=WxH            [180x180]
 --show-geo                   [%(show_geo)s]
 --correct-orientation        [%(correct_orientation)s]
 --skip-image-gen             [%(skip_image_gen)s]
 --skip-thumb-gen             [%(skip_thumb_gen)s]
"""


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
    s = arg.split('x')
    return [int(s[0]), int(s[1])]


# option -> (opts key, argument converter)
OPTIONS: dict[str, tuple[str, Callable[[str], Any]]] = {
    '--album-name': ('album_name', str),
    '--album-dir': ('album_dir', str),
    '--album-format': ('album_format', str.lower),
    '--path': ('path', str),
    '--copyright': ('copyright', str),
    '--template': ('template', str),
    '--style': ('style', str),
    '--ppp': ('ppp', int),
    '--show-geo': ('show_geo', lambda arg: bool(int(arg))),
    '--correct-orientation': ('correct_orientation', lambda arg: bool(int(arg))),
    '--images-format': ('images_format', str),
    '--images-quality': ('images_quality', int),
    '--images-sharpness': ('images_sharpness', float),
    '--images-maxsize': ('images_maxsize', _size),
    '--images-default-size': ('default_image_size', _size),
    '--thumbs-skip': ('thumbs_skip', lambda arg: True),
    '--thumbs-quality': ('thumbs_quality', int),
    '--thumbs-size': ('thumbs_size', lambda arg: tuple(_size(arg))),
    '--skip-image-gen': ('skip_image_gen', lambda arg: True),
    '--skip-thumb-gen': ('skip_thumb_gen', lambda arg: True),
}


def parse_args(opts: dict[str, Any], argv: list[str]) -> None:
    """Apply command line options to `opts`. Raises getopt.GetoptError."""
    gopts, args = getopt.getopt(argv, '', LONG_OPTIONS)
    for o, arg in gopts:
        if o == '--help':
            raise getopt.GetoptError('')
        key, convert = OPTIONS[o]
        opts[key] = convert(arg)

    if len(args) < 2:
        raise getopt.GetoptError('')
    opts['inputdir'] = args[0]
    opts['outputdir'] = args[1]


def main(argv: list[str] | None = None) -> None:
    opts = default_opts()
    try:
        parse_args(opts, sys.argv[1:] if argv is None else argv)
    except getopt.GetoptError:
        print(f'Usage: {sys.argv[0]} [OPTION...] INPUT-DIR OUTPUT-DIR')
        print(f'{sys.argv[0]} -- album generator')
        print(USAGE % opts)
        sys.exit(1)

    os.makedirs(opts['outputdir'], exist_ok=True)

    album = new_album(opts)
    opts['idx'] = 1
    for fname in list_input_files(opts):
        if fname.lower().endswith('.jpg') or fname.lower().endswith('.jpeg'):
            process_image(opts, album, fname)
            opts['idx'] += 1

    album_name = (
        opts['album_name'] or os.path.basename(opts['outputdir'].rstrip('/')) or 'foo'
    )
    album_dir = opts['album_dir'] or opts['outputdir']

    if opts['album_format'] in ('json', 'all'):
        write_json(os.path.normpath(f'{album_dir}/{album_name}.json'), album)
    if opts['album_format'] in ('yaml', 'all'):
        write_yaml(os.path.normpath(f'{album_dir}/{album_name}.yaml'), album)

    print('done')


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
        'default_image_size': opts.get('default_image_size', []),
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
