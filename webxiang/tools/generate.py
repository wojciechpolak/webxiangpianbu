#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  WebXiangpianbu Copyright (C) 2013 Wojciech Polak
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
        'album-name': None,
        'album-dir': None,
        'album-format': 'yaml',
        'copyright': None,
        'template': None,
        'style': None,
        'images-quality': 95,
        'images-maxsize': [900, 640],
        'images-sharpness': 1.4,
        'thumbs-skip': False,
        'thumbs-quality': 90,
        'thumbs-size': [180, 180],
        'show-geo': True,
        'correct-orientation': True,
        'skip-image-gen': False,
        'skip-thumb-gen': False,
    }

    try:
        gopts, args = getopt.getopt(sys.argv[1:], '',
                                    ['album-name=',
                                     'album-dir=',
                                     'album-format=',
                                     'copyright=',
                                     'template=',
                                     'style=',
                                     'images-quality=',
                                     'images-sharpness=',
                                     'images-maxsize=',
                                     'images-default-size=',
                                     'thumbs-skip',
                                     'thumbs-quality=',
                                     'thumbs-size=',
                                     'show-geo',
                                     'correct-orientation',
                                     'skip-image-gen',
                                     'skip-thumb-gen',
                                     ])
        for o, arg in gopts:
            if o == '--album-name':
                opts['album-name'] = arg
            elif o == '--album-dir':
                opts['album-dir'] = arg
            elif o == '--album-format':
                opts['album-format'] = arg.lower()
            elif o == '--copyright':
                opts['copyright'] = arg
            elif o == '--template':
                opts['template'] = arg
            elif o == '--style':
                opts['style'] = arg
            elif o == '--show-geo':
                opts['show-geo'] = True

            elif o in ('-q', '--images-quality'):
                opts['images-quality'] = int(arg)
            elif o == '--images-sharpness':
                opts['images-sharpness'] = float(arg)
            elif o == '--images-maxsize':
                s = arg.split('x')
                opts['images-maxsize'] = [int(s[0]), int(s[1])]
            elif o == '--images-default-size':
                s = arg.split('x')
                opts['default-image-size'] = [int(s[0]), int(s[1])]

            elif o == '--thumbs-skip':
                opts['thumbs-skip'] = True
            elif o == '--thumbs-quality':
                opts['thumbs-quality'] = int(arg)
            elif o == '--thumbs-size':
                s = arg.split('x')
                opts['thumbs-size'] = int(s[0]), int(s[1])

            elif o == '--skip-image-gen':
                opts['skip-image-gen'] = True
            elif o == '--skip-thumb-gen':
                opts['skip-thumb-gen'] = True

        opts['inputdir'] = args[0]
        opts['outputdir'] = args[1]
    except getopt.GetoptError:
        print "Usage: %s [OPTION...] INPUT-DIR OUTPUT-DIR" % sys.argv[0]
        print "%s -- album generator" % sys.argv[0]
        sys.exit(1)

    if not os.path.exists(opts['outputdir']):
        os.makedirs(opts['outputdir'])

    album = {
        'meta': {
            'path': '',
            'title': '',
            'ppp': 12,
            'columns': 4,
            'copyright': '%s' % date.today().year,
            'default-image-size': [],
            'default-thumb-size': opts['thumbs-size'],
        },
        'entries': [],
    }

    if 'copyright' in opts:
        album['meta']['copyright'] = opts['copyright']
    if 'template' in opts:
        album['meta']['template'] = opts['template']
        album['meta']['thumbs-skip'] = True
    if 'style' in opts:
        album['meta']['style'] = opts['style']
    if 'show-geo' in opts:
        album['meta']['geo'] = True
    if 'default-image-size' in opts:
        album['meta']['default-image-size'] = opts['default-image-size']

    if opts['inputdir'].endswith('.in'):
        fp = open(opts['inputdir'])
        data = fp.readlines()
        fp.close()
        opts['inputdir'] = data[0].strip()  # first line points directory
        files = [line.strip() for line in data[1:] if line.strip()]
    else:
        files = os.listdir(opts['inputdir'])
        files.sort()

    opts['idx'] = 1
    for fname in files:
        if fname.lower().endswith('.jpg'):
            process_image(opts, album, fname)
            opts['idx'] += 1

    album_name = opts['album-name'] or \
        os.path.basename(opts['outputdir']) or 'foo'
    album['meta']['path'] = album_name + '/'

    if 'album-dir' in opts:
        album_dir = opts['album-dir']
    else:
        album_dir = opts['outputdir']

    if opts['album-format'] in ('json', 'all'):
        # output json
        filename = os.path.normpath('%s/%s.json' % (album_dir, album_name))
        overwrite = True
        if os.path.exists(filename):
            overwrite = confirm('Overwrite album file %s?' % filename)
        if overwrite:
            album_file_json = file(filename, 'w')
            json.dump(album, album_file_json, indent=4)
            album_file_json.write('\n')
            album_file_json.close()
            print 'saved %s' % album_file_json.name

    if opts['album-format'] in ('yaml', 'all'):
        # output yaml
        filename = os.path.normpath('%s/%s.yaml' % (album_dir, album_name))
        overwrite = True
        if os.path.exists(filename):
            overwrite = confirm('Overwrite album file %s?' % filename)
        if overwrite:
            album_file_yaml = file(filename, 'w')
            yaml.dump(album, album_file_yaml, encoding='utf-8',
                      default_flow_style=None, indent=4, width=70)
            album_file_yaml.close()
            print 'saved %s' % album_file_yaml.name

    print 'done'


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
    img = Image.open(opts['inputdir'] + fname)

    # lower case for file suffix
    fn = fname.split('.')
    fname = '%s.%s' % (''.join(fn[0:-1]), fn[-1].lower())

    data = {
        'idx': opts['idx'],
        'image': fname,
    }

    if img.mode != 'RGB':
        img = img.convert('RGB')

    try:
        exif = img._getexif()
    except:
        exif = None

    gps_data = {}
    exif_data = {}
    exif_accepted = set(exif_tags.keys())

    if exif != None:
        for tag, value in exif.items():
            decoded = ExifTags.TAGS.get(tag, tag)
            if decoded in exif_accepted:
                exif_data[decoded] = value
            elif decoded == 'Orientation':
                if opts['correct-orientation']:
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

    for k, v in exif_data.items():
        exif_data[k] = exif_tags[k](v)
    if exif_data:
        data['exif'] = exif_data

    if not opts['thumbs-skip']:
        data['thumb'] = gen_thumbnails(opts, img, fname)

    lat, lng = get_latlng(gps_data)
    if lat and lng:
        data['geo'] = '%s,%s' % (lat, lng)

    album['entries'].append(data)

    img.thumbnail(opts['images-maxsize'], Image.ANTIALIAS)
    if list(img.size) != album['meta']['default-image-size']:
        data['image'] = {'file': fname, 'size': list(img.size)}

    if not opts['skip-image-gen']:
        if opts['images-sharpness']:
            sharpener = ImageEnhance.Sharpness(img)
            img = sharpener.enhance(opts['images-sharpness'])

        ImageFile.MAXBLOCK = img.size[0] * img.size[1]
        img.save(opts['outputdir'] + '/' + fname, 'JPEG', optimize=True,
                 quality=opts['images-quality'], progressive=False)

        print 'saved %s' % opts['outputdir'] + '/' + fname


def gen_thumbnails(opts, img_blob, fname):
    size = opts['thumbs-size']
    fn = fname.split('.')
    fname = '%s-%dx%d.%s' % (''.join(fn[0:-1]), size[0], size[1], fn[-1])

    if opts['skip-thumb-gen']:
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
    img.save(opts['outputdir'] + '/' + fname, 'JPEG', optimize=True,
             quality=opts['thumbs-quality'], progressive=True)

    print 'saved %s' % opts['outputdir'] + '/' + fname
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
        res = raw_input("%s [%s] " % (question, defval)).lower()
        if not res:
            return default
        elif res in ('y', 'yes'):
            return True
        elif res in ('n', 'no'):
            return False


if __name__ == '__main__':
    main()
