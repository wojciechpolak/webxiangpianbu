#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  WebXiangpianbu Copyright (C) 2013, 2014, 2015 Wojciech Polak
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
#  with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import getopt
import yaml
from datetime import date
from django.utils.six.moves import input

try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = None

try:
    import simplejson as json
except ImportError:
    import json

try:
    from PIL import Image
    from PIL import ImageFile
    from PIL import ImageEnhance
    from PIL import ExifTags
except ImportError:
    import Image
    import ImageFile
    import ImageEnhance
    import ExifTags


def main():
    opts = {
        'album_name': None,
        'album_dir': None,
        'album_format': 'yaml',
        'path': '',
        'copyright': '',
        'template': 'default',
        'style': 'base',
        'ppp': 12,  # pictures per page
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

    try:
        gopts, args = getopt.getopt(sys.argv[1:], '',
                                    ['help',
                                     'album-name=',
                                     'album-dir=',
                                     'album-format=',
                                     'path=',
                                     'copyright=',
                                     'template=',
                                     'style=',
                                     'ppp=',
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
                                     ])
        for o, arg in gopts:
            if o == '--help':
                raise getopt.GetoptError('')
            elif o == '--album-name':
                opts['album_name'] = arg
            elif o == '--album-dir':
                opts['album_dir'] = arg
            elif o == '--album-format':
                opts['album_format'] = arg.lower()
            elif o == '--path':
                opts['path'] = arg
            elif o == '--copyright':
                opts['copyright'] = arg
            elif o == '--template':
                opts['template'] = arg
            elif o == '--style':
                opts['style'] = arg
            elif o == '--ppp':
                opts['ppp'] = int(arg)
            elif o == '--show-geo':
                opts['show_geo'] = bool(int(arg))
            elif o == '--correct-orientation':
                opts['correct_orientation'] = bool(int(arg))

            elif o in ('-q', '--images-quality'):
                opts['images_quality'] = int(arg)
            elif o == '--images-sharpness':
                opts['images_sharpness'] = float(arg)
            elif o == '--images-maxsize':
                s = arg.split('x')
                opts['images_maxsize'] = [int(s[0]), int(s[1])]
            elif o == '--images-default-size':
                s = arg.split('x')
                opts['default_image_size'] = [int(s[0]), int(s[1])]

            elif o == '--thumbs-skip':
                opts['thumbs_skip'] = True
            elif o == '--thumbs-quality':
                opts['thumbs_quality'] = int(arg)
            elif o == '--thumbs-size':
                s = arg.split('x')
                opts['thumbs_size'] = int(s[0]), int(s[1])

            elif o == '--skip-image-gen':
                opts['skip_image_gen'] = True
            elif o == '--skip-thumb-gen':
                opts['skip_thumb_gen'] = True

        if len(args):
            opts['inputdir'] = args[0]
            opts['outputdir'] = args[1]
        else:
            raise getopt.GetoptError('')
    except getopt.GetoptError:
        print("Usage: %s [OPTION...] INPUT-DIR OUTPUT-DIR" % sys.argv[0])
        print("%s -- album generator" % sys.argv[0])
        print("""
 Options                      Default values
 --album-name=STRING          [output dir's name]
 --album-dir=STRING           [output dir]
 --album-format=STRING        [%(album_format)s] (yaml|json|all)
 --path=STRING                ['']
 --copyright=STRING           ['']
 --template=STRING            [''] (default|floating|story)
 --style=STRING               ['']
 --ppp=INTEGER                [%(ppp)s]
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
""" % opts)
        sys.exit(1)

    if not os.path.exists(opts['outputdir']):
        os.makedirs(opts['outputdir'])

    album = {
        'meta': {
            'path': opts['path'],
            'title': '',
            'ppp': opts['ppp'],
            'columns': 4,
            'template': opts['template'],
            'thumbs_skip': opts['thumbs_skip'],
            'style': opts['style'],
            'copyright': '%s' % date.today().year,
            'geo': opts['show_geo'],
            'default_image_size': [],
            'default_thumb_size': opts['thumbs_size'],
        },
        'entries': [],
    }

    if opts['copyright']:
        album['meta']['copyright'] = opts['copyright']
    if opts['template'] == 'story':
        album['meta']['thumbs_skip'] = True
    if 'default_image_size' in opts:
        album['meta']['default_image_size'] = opts['default_image_size']

    if opts['inputdir'].endswith('.in'):
        with open(opts['inputdir']) as fp:
            data = fp.readlines()
        opts['inputdir'] = data[0].strip()  # first line points directory
        files = []
        for line in data[1:]:
            line = line.split('#')[0].strip()
            if line:
                files.append(line)
    else:
        files = os.listdir(opts['inputdir'])
        files.sort()

    opts['idx'] = 1
    for fname in files:
        if fname.lower().endswith('.jpg'):
            process_image(opts, album, fname)
            opts['idx'] += 1

    album_name = opts['album_name'] or \
        os.path.basename(opts['outputdir'].rstrip('/')) or 'foo'

    album_dir = opts['album_dir'] or opts['outputdir']

    if opts['album_format'] in ('json', 'all'):
        # output json
        filename = os.path.normpath('%s/%s.json' % (album_dir, album_name))
        overwrite = True
        if os.path.exists(filename):
            overwrite = confirm('Overwrite album file %s?' % filename)
        if overwrite:
            with open(filename, 'w') as album_file_json:
                json.dump(album, album_file_json, indent=4)
                album_file_json.write('\n')
                print('saved %s' % album_file_json.name)

    if opts['album_format'] in ('yaml', 'all'):
        # output yaml
        filename = os.path.normpath('%s/%s.yaml' % (album_dir, album_name))
        overwrite = True
        if os.path.exists(filename):
            overwrite = confirm('Overwrite album file %s?' % filename)
        if overwrite:
            if OrderedDict:
                def order_rep(dumper, data):
                    return dumper.represent_mapping(u'tag:yaml.org,2002:map',
                                                    list(data.items()),
                                                    flow_style=False)
                yaml.add_representer(OrderedDict, order_rep)
                album = OrderedDict({
                        'meta': album['meta'],
                        'entries': album['entries'],
                        })

            with open(filename, 'w') as album_file_yaml:
                yaml.dump(album, album_file_yaml, encoding='utf-8',
                          default_flow_style=None, indent=4, width=70)
                print('saved %s' % album_file_yaml.name)

    print('done')


exif_tags = {
    'ApertureValue': lambda v: 'f/%s' % round(v[0] / float(v[1]), 1),
    'DateTimeOriginal': lambda v: v,
    'ExposureBiasValue': lambda v: '%s EV' % v,
    'ExposureTime': lambda v: '%s/%s sec' % (v[0], v[1]),
    'FNumber': lambda v: 'f/%s' % round(v[0] / float(v[1]), 1),
    'FocalLength': lambda v: '%smm' % v[0],
    'ISOSpeedRatings': lambda v: v,
    'LensMake': lambda v: v,
    'LensModel': lambda v: v,
    'Make': lambda v: v,
    'Model': lambda v: v,
}


def process_image(opts, album, fname):
    img = Image.open(os.path.join(opts['inputdir'], fname))

    # lower case for file suffix
    fn = fname.split('.')
    fname = '%s.%s' % (''.join(fn[0:-1]), fn[-1].lower())

    data = OrderedDict() if OrderedDict else {}
    data['idx'] = opts['idx']
    data['image'] = fname

    if img.mode != 'RGB':
        img = img.convert('RGB')

    if not opts['thumbs_skip']:
        data['thumb'] = gen_thumbnails(opts, img, fname)

    try:
        exif = img._getexif()
    except:
        exif = None

    gps_data = {}
    exif_data = {}
    exif_accepted = set(exif_tags.keys())

    if exif != None:
        for tag, value in list(exif.items()):
            decoded = ExifTags.TAGS.get(tag, tag)
            if decoded in exif_accepted:
                exif_data[decoded] = value
            elif decoded == 'Orientation':
                if opts['correct_orientation']:
                    if value == 3:
                        img = img.rotate(180)
                    if value == 6:
                        img = img.rotate(270)
                    if value == 8:
                        img = img.rotate(90)
            elif decoded == 'GPSInfo':
                for t in value:
                    sub_decoded = ExifTags.GPSTAGS.get(t, t)
                    gps_data[sub_decoded] = value[t]

    for k, v in list(exif_data.items()):
        exif_data[k] = str(exif_tags[k](v)).strip()

    lat, lng = get_latlng(gps_data)
    if lat and lng:
        data['geo'] = '%s,%s' % (lat, lng)

    if exif_data:
        data['exif'] = exif_data

    album['entries'].append(data)

    img.thumbnail(opts['images_maxsize'], Image.ANTIALIAS)
    if list(img.size) != album['meta']['default_image_size']:
        data['image'] = {'file': fname, 'size': list(img.size)}

    output_fname = os.path.join(opts['outputdir'], fname)
    if os.path.exists(output_fname):
        print('file exists, skipping... %s' % output_fname)
        return

    if not opts['skip_image_gen']:
        if opts['images_sharpness']:
            sharpener = ImageEnhance.Sharpness(img)
            img = sharpener.enhance(opts['images_sharpness'])

        ImageFile.MAXBLOCK = img.size[0] * img.size[1]
        img.save(output_fname, 'JPEG', optimize=True,
                 quality=opts['images_quality'], progressive=False)

        print('saved %s' % output_fname)


def gen_thumbnails(opts, img_blob, fname):
    size = opts['thumbs_size']
    fn = fname.split('.')
    fname = '%s-%dx%d.%s' % (''.join(fn[0:-1]), size[0], size[1], fn[-1])

    if opts['skip_thumb_gen']:
        return fname

    output_fname = os.path.join(opts['outputdir'], fname)
    if os.path.exists(output_fname):
        print('file exists, skipping... %s' % output_fname)
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
    img.thumbnail(size, Image.ANTIALIAS)
    ImageFile.MAXBLOCK = 131072
    img.save(output_fname, 'JPEG', optimize=True,
             quality=opts['thumbs_quality'], progressive=True)

    print('saved %s' % output_fname)
    return fname


def _geo_convert_to_degress(value):
    d0 = value[0][0]
    d1 = value[0][1]
    d = float(d0) / float(d1)

    m0 = value[1][0]
    m1 = value[1][1]
    m = float(m0) / float(m1)

    s0 = value[2][0]
    s1 = value[2][1]
    s = float(s0) / float(s1)
    return d + (m / 60.0) + (s / 3600.0)


def get_latlng(gps_data):
    lat = None
    lng = None

    gps_latitude = gps_data.get('GPSLatitude')
    gps_latitude_ref = gps_data.get('GPSLatitudeRef')
    gps_longitude = gps_data.get('GPSLongitude')
    gps_longitude_ref = gps_data.get('GPSLongitudeRef')

    if gps_latitude and gps_latitude_ref and gps_longitude \
            and gps_longitude_ref:
        lat = _geo_convert_to_degress(gps_latitude)
        if gps_latitude_ref != 'N':
            lat = 0 - lat

        lng = _geo_convert_to_degress(gps_longitude)
        if gps_longitude_ref != 'E':
            lng = 0 - lng

    if lat and lng:
        return round(lat, 6), round(lng, 6)
    else:
        return None, None


def confirm(question, default=False):
    if default:
        defval = 'Y/n'
    else:
        defval = 'y/N'
    while True:
        res = input("%s [%s] " % (question, defval)).lower()
        if not res:
            return default
        elif res in ('y', 'yes'):
            return True
        elif res in ('n', 'no'):
            return False


if __name__ == '__main__':
    main()
