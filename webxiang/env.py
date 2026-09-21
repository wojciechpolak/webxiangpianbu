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

Environment helpers for the settings modules.

No Django imports here: settings import this before Django is configured.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

_TRUE_VALUES = {'1', 'true', 'yes', 'on'}
_FALSE_VALUES = {'0', 'false', 'no', 'off'}


def _parse_dotenv_line(raw_line: str) -> tuple[str, str] | None:
    line = raw_line.strip()
    if not line or line.startswith('#'):
        return None
    line = line.removeprefix('export ').strip()
    name, sep, value = line.partition('=')
    name = name.strip()
    if not sep or not name:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return name, value


def load_dotenv(path: str | os.PathLike[str]) -> None:
    """Load `NAME=value` lines from a .env file into os.environ.

    Variables already set in the environment win over the file."""
    env_path = Path(path)
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        parsed = _parse_dotenv_line(raw_line)
        if parsed:
            os.environ.setdefault(*parsed)


def get_env(env: Mapping[str, str], *names: str, default: str = '') -> str:
    """The first non-empty value among `names`, else `default`."""
    for name in names:
        value = env.get(name)
        if value:
            return value
    return default


def get_bool(env: Mapping[str, str], *names: str, default: bool) -> bool:
    value = get_env(env, *names).strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    return default


def get_list(env: Mapping[str, str], *names: str, default: list[str]) -> list[str]:
    """A comma-separated value as a list, blanks dropped."""
    value = get_env(env, *names)
    if not value:
        return list(default)
    return [item.strip() for item in value.split(',') if item.strip()]
