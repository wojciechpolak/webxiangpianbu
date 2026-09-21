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

from types import SimpleNamespace
from typing import cast

import pytest

from tests.coverage_report import (
    coverage_enabled,
    describe_narrowed_run,
)


def fake_config(
    *, markexpr: str = '', keyword: str = '', args_source=None
) -> pytest.Config:
    return cast(
        pytest.Config,
        SimpleNamespace(
            option=SimpleNamespace(markexpr=markexpr, keyword=keyword),
            args_source=args_source or pytest.Config.ArgsSource.INVOCATION_DIR,
        ),
    )


def test_a_plain_run_is_not_narrowed():
    assert describe_narrowed_run(fake_config()) == ''


def test_testpaths_still_count_as_a_full_run():
    config = fake_config(args_source=pytest.Config.ArgsSource.TESTPATHS)

    assert describe_narrowed_run(config) == ''


def test_a_marker_expression_narrows_the_run():
    assert describe_narrowed_run(fake_config(markexpr='e2e')) == '-m e2e'


def test_a_keyword_expression_narrows_the_run():
    assert describe_narrowed_run(fake_config(keyword='urlize')) == '-k urlize'


def test_explicit_paths_narrow_the_run():
    config = fake_config(args_source=pytest.Config.ArgsSource.ARGS)

    assert describe_narrowed_run(config) == 'an explicit test selection'


def test_a_marker_is_reported_ahead_of_a_keyword():
    config = fake_config(markexpr='e2e', keyword='urlize')

    assert describe_narrowed_run(config) == '-m e2e'


def fake_cov_config(**options) -> pytest.Config:
    options.setdefault('no_cov', False)
    options.setdefault('cov_source', None)
    options.setdefault('cov_report', None)
    return cast(pytest.Config, SimpleNamespace(option=SimpleNamespace(**options)))


def test_coverage_is_enabled_by_a_configured_source():
    assert coverage_enabled(fake_cov_config(cov_source=['webxiang'])) is True


def test_coverage_is_enabled_by_a_configured_report():
    assert coverage_enabled(fake_cov_config(cov_report={'term': None})) is True


def test_no_cov_wins_over_a_configured_source():
    config = fake_cov_config(cov_source=['webxiang'], no_cov=True)

    assert coverage_enabled(config) is False


def test_coverage_is_off_when_nothing_configured_it():
    assert coverage_enabled(fake_cov_config()) is False
