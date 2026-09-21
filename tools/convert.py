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
import glob
import json
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


def parse_args(opts: dict[str, Any], argv: list[str]) -> None:
    """Apply command line options to `opts`. Raises getopt.GetoptError."""
    gopts, args = getopt.getopt(argv, 'y', ['overwrite='])
    for o, _arg in gopts:
        if o in ('-y', '--overwrite'):
            opts['overwrite'] = True

    if not args:
        raise getopt.GetoptError('')
    opts['input'] = glob.glob(args[0])
    if len(args) > 1:
        opts['output_dir'] = os.path.dirname(args[1])
        opts['output_name'] = os.path.basename(args[1])


def default_opts() -> dict[str, Any]:
    return {
        'overwrite': False,
        'output_dir': '',
        'output_name': '',
    }


def main(argv: list[str] | None = None) -> None:
    opts = default_opts()

    try:
        parse_args(opts, sys.argv[1:] if argv is None else argv)
    except getopt.GetoptError:
        print(f'Usage: {sys.argv[0]} [OPTION...] INPUT OUTPUT')
        print(f'{sys.argv[0]} -- album converter')
        print("""
 Options               Default values
 -y, --overwrite       [False]
""")
        sys.exit(1)

    if opts['output_dir']:
        os.makedirs(opts['output_dir'], exist_ok=True)

    for name in opts['input']:
        convert_file(opts, name)
    print('done')


def convert_file(opts: dict[str, Any], name: str) -> None:
    """Write a JSON album file out as YAML, or a YAML one as JSON."""
    data = read_albumfile(name)
    if not data:
        return
    if name.endswith('.json'):
        to_yaml(opts, name, data)
    elif name.endswith('.yaml'):
        to_json(opts, name, data)


def read_albumfile(name: str) -> dict[str, Any] | None:
    if os.path.isfile(name) and name.endswith('.yaml'):
        try:
            with open(name, 'r', encoding='utf-8') as fp:
                return cast(dict[str, Any], yaml.load(fp, Loader=YamlLoader))
        except (OSError, yaml.YAMLError) as e:
            print(e)
    elif os.path.isfile(name) and name.endswith('.json'):
        try:
            with open(name, 'r', encoding='utf-8') as fp:
                return cast(dict[str, Any], json.load(fp))
        except (OSError, ValueError) as e:
            print(e)
    return None


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
