#!/usr/bin/env python3

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

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='webxiang/settings_sample.py')
    parser.add_argument('--output', default='/tmp/vrt_settings.py')
    parser.add_argument('--site-root', default='/work/webxiang')
    parser.add_argument('--secret-key', default='ci-secret-key')
    args = parser.parse_args()

    source_path = Path(args.source)
    output_path = Path(args.output)
    source = source_path.read_text(encoding='utf-8')
    source = source.replace(
        'SITE_ROOT = os.path.dirname(os.path.realpath(__file__))',
        f'SITE_ROOT = "{args.site_root}"',
    )
    source = source.replace(
        "SECRET_KEY = os.getenv('WEBXIANG_SECRET_KEY', '')",
        f'SECRET_KEY = "{args.secret_key}"',
    )
    source += (
        '\n\nDATABASES = {\n'
        "    'default': {\n"
        "        'ENGINE': 'django.db.backends.sqlite3',\n"
        "        'NAME': '/tmp/vrt-settings.sqlite3',\n"
        '    }\n'
        '}\n'
    )
    output_path.write_text(source, encoding='utf-8')


if __name__ == '__main__':
    main()
