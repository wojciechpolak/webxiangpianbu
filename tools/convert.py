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
import glob
import json
import logging
import os
import sys
from typing import Any, cast

yaml: Any = None
YamlLoader: Any = None
YamlDumper: Any = None

try:
    import yaml as _yaml

    yaml = _yaml

    YamlLoader = cast(Any, getattr(_yaml, 'CLoader', _yaml.Loader))
    YamlDumper = cast(Any, getattr(_yaml, 'CDumper', _yaml.Dumper))
except ImportError:
    yaml = None


logger = logging.getLogger('tools.convert')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Convert album files between YAML and JSON.'
    )
    parser.add_argument(
        '-y',
        '--overwrite',
        action='store_true',
        help='overwrite existing output files without asking',
    )
    parser.add_argument(
        'input', help="album file, or a quoted glob pattern like 'albums/*.yaml'"
    )
    parser.add_argument(
        'output',
        nargs='?',
        default='',
        help='output file, or a directory when it ends with "/" '
        '(default: next to each input)',
    )
    return parser


def parse_args(argv: list[str]) -> dict[str, Any]:
    parser = build_parser()
    args = parser.parse_args(argv)
    inputs = glob.glob(args.input)
    if not inputs:
        parser.error(f'no album files match {args.input!r}')
    return {
        'overwrite': args.overwrite,
        'input': inputs,
        'output_dir': os.path.dirname(args.output),
        'output_name': os.path.basename(args.output),
    }


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(format='%(levelname)s: %(message)s')
    opts = parse_args(sys.argv[1:] if argv is None else argv)

    if opts['output_dir']:
        os.makedirs(opts['output_dir'], exist_ok=True)

    failed = [name for name in opts['input'] if not convert_file(opts, name)]
    if failed:
        sys.exit(1)
    print('done')


def convert_file(opts: dict[str, Any], name: str) -> bool:
    """Write a JSON album file out as YAML, or a YAML one as JSON. False when
    `name` could not be read."""
    if not name.endswith(('.json', '.yaml')):
        logger.warning('skipping %s: not a .json or .yaml file', name)
        return True
    data = read_albumfile(name)
    if data is None:
        return False
    if name.endswith('.json'):
        to_yaml(opts, name, data)
    else:
        to_json(opts, name, data)
    return True


def read_albumfile(name: str) -> dict[str, Any] | None:
    """The album in a .yaml or .json file, or None (after logging why) when
    it cannot be read."""
    try:
        with open(name, 'r', encoding='utf-8') as fp:
            if name.endswith('.yaml'):
                data = yaml.load(fp, Loader=YamlLoader)
            else:
                data = json.load(fp)
    except (OSError, ValueError, yaml.YAMLError) as e:
        logger.error('cannot read %s: %s', name, e)
        return None
    if not isinstance(data, dict):
        logger.error('cannot read %s: not an album (expected a mapping)', name)
        return None
    return data


def to_yaml(opts: dict[str, Any], name: str, data: dict[str, Any]) -> None:
    filename = os.path.join(
        opts['output_dir'] or os.path.dirname(name),
        opts['output_name'] or os.path.basename(name.replace('.json', '.yaml')),
    )
    overwrite = True
    if os.path.exists(filename):
        overwrite = opts['overwrite'] or confirm(f'Overwrite album file {filename}?')
    if overwrite:
        with open(filename, 'w', encoding='utf-8') as album_file_yaml:
            yaml.dump(
                data,
                album_file_yaml,
                encoding='utf-8',
                allow_unicode=True,
                default_flow_style=False,
                indent=4,
                width=70,
                Dumper=YamlDumper,
            )
            print(f'saved {album_file_yaml.name}')


def to_json(opts: dict[str, Any], name: str, data: dict[str, Any]) -> None:
    filename = os.path.join(
        opts['output_dir'] or os.path.dirname(name),
        opts['output_name'] or os.path.basename(name.replace('.yaml', '.json')),
    )
    overwrite = True
    if os.path.exists(filename):
        overwrite = opts['overwrite'] or confirm(f'Overwrite album file {filename}?')
    if overwrite:
        with open(filename, 'w', encoding='utf-8') as album_file_json:
            json.dump(data, album_file_json, indent=4)
            album_file_json.write('\n')
            print(f'saved {album_file_json.name}')


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
