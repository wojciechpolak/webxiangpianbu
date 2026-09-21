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

import pytest

COVERAGE_LCOV = 'coverage.lcov'
COVERAGE_HTML_DIR = 'htmlcov'


def coverage_enabled(config: pytest.Config) -> bool:
    return not bool(getattr(config.option, 'no_cov', False)) and bool(
        getattr(config.option, 'cov_source', None)
        or getattr(config.option, 'cov_report', None)
    )


def describe_narrowed_run(config: pytest.Config) -> str:
    """How this run was narrowed, or '' when it covers the whole suite.

    A narrowed run measures the same lines as a full one but exercises far
    fewer of them: `-m e2e` reports around 26% where the full suite reports
    47%. Both are honest about what they ran, so publishing either into the
    shared report files means whichever finished last wins -- and the CRAP
    tooling reads those files, not the terminal.
    """
    markexpr = getattr(config.option, 'markexpr', '')
    if markexpr:
        return '-m %s' % markexpr
    keyword = getattr(config.option, 'keyword', '')
    if keyword:
        return '-k %s' % keyword
    if getattr(config, 'args_source', None) == pytest.Config.ArgsSource.ARGS:
        return 'an explicit test selection'
    return ''
