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

import os

import pytest

from webxiang.env import get_bool, get_env, get_list, load_dotenv


def test_load_dotenv_parses_lines_and_keeps_existing_env(tmp_path, monkeypatch):
    for name in ('WXT_PLAIN', 'WXT_EXPORTED', 'WXT_DOUBLE', 'WXT_SINGLE', 'WXT_EQ'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('WXT_SET', 'from-env')
    env_file = tmp_path / '.env'
    env_file.write_text(
        '\n'.join(
            [
                '# a comment',
                '',
                'WXT_PLAIN = plain ',
                'export WXT_EXPORTED=exported',
                'WXT_DOUBLE="double quoted"',
                "WXT_SINGLE=' single '",
                'WXT_EQ=a=b',
                'WXT_SET=from-file',
                'no equals sign',
                '=no-name',
            ]
        ),
        encoding='utf-8',
    )

    load_dotenv(env_file)

    assert os.environ['WXT_PLAIN'] == 'plain'
    assert os.environ['WXT_EXPORTED'] == 'exported'
    assert os.environ['WXT_DOUBLE'] == 'double quoted'
    assert os.environ['WXT_SINGLE'] == ' single '
    assert os.environ['WXT_EQ'] == 'a=b'
    assert os.environ['WXT_SET'] == 'from-env'


def test_load_dotenv_ignores_missing_file(tmp_path):
    load_dotenv(tmp_path / 'missing.env')


def test_get_env_returns_first_non_empty_name():
    env = {'A': '', 'B': 'b', 'C': 'c'}

    assert get_env(env, 'A', 'B', 'C') == 'b'
    assert get_env(env, 'A', 'X', default='d') == 'd'
    assert get_env(env, 'X') == ''


@pytest.mark.parametrize(
    ('value', 'expected'),
    [('1', True), (' Yes ', True), ('on', True), ('0', False), ('OFF', False)],
)
def test_get_bool_parses_known_values(value, expected):
    assert get_bool({'FLAG': value}, 'FLAG', default=not expected) is expected


@pytest.mark.parametrize('env', [{}, {'FLAG': 'maybe'}])
def test_get_bool_falls_back_to_default(env):
    assert get_bool(env, 'FLAG', default=True) is True
    assert get_bool(env, 'FLAG', default=False) is False


def test_get_list_splits_on_commas():
    assert get_list({'L': ' a, b ,,c '}, 'L', default=[]) == ['a', 'b', 'c']


def test_get_list_default_is_a_copy():
    default = ['x']
    result = get_list({}, 'L', default=default)

    assert result == ['x']
    assert result is not default
