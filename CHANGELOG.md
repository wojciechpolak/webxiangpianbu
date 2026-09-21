# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Entries before the first GitHub release were reconstructed from git tags
and history and only list the major changes.

## [Unreleased]

### Added

- Dark mode.
- HTML5 video entries with multiple sources (`VideoSrc`, optional `media`
  attribute).
- Docker deployment: Docker Compose setup with Nginx as a separate service,
  gunicorn (replacing uWSGI), multi-platform images published to GHCR with
  GitHub build attestations.
- Test suite: pytest unit tests, Playwright end-to-end tests and optional
  visual regression tests run in Docker.
- Type hints for the codebase and album schema, checked with mypy and ty.
- CI workflow running ruff, ty, mypy and pytest, with branch coverage.

### Changed

- Python 3 only; upgraded through Django 3.2, 4.2 and 5.x.
- `webxiang/settings.py` is now committed and configured through environment
  variables and an optional `.env` file, replacing the copied
  `settings_sample.py`. Local tweaks go in an optional `settings_local.py`.
- Photos use the browser's native lazy loading.
- Simplified album caching.
- Dependency management moved to Poetry and then to uv.

### Security

- The sample settings no longer ship a usable secret key.

## [2.1] - 2021-02-16

### Added

- Static site generator (`tools/staticgen.py`).
- `light` style.
- Leaflet and Mapbox map support.
- Python 3 support.

### Changed

- Upgraded to Django 1.7 and then 1.11.
- Static assets are managed with django-pipeline.
- Larger geomap view.

### Removed

- Google Maps support.

## [2.0] - 2014-02-20

Complete rewrite in Python/Django.

### Added

- Albums defined as YAML or JSON files, no database required.
- `default`, `floating` and `story` templates, with customizable styles.
- Mobile-friendly layout with swipe navigation.
- Keyboard shortcuts and a help dialog (`?`).
- Geomap view for the photos of an album.
- Canonical URLs and slugs, meta descriptions and cover images.
- Photo lazy loading plugin support.
- `tools/generate.py` to build albums from photo directories and
  `tools/convert.py` to convert albums between YAML and JSON.
- Localization.

### Removed

- The PHP implementation and XML album format.

## 1.1 – 1.4 - 2006-2010

PHP releases, not tagged.

### Added

- Web feed for albums (1.4).

### Changed

- Relicensed under GPL v3 (1.2).

## [1.0] - 2005-12-23

First stable release of the PHP gallery, with XML albums and JavaScript
navigation. Released under the GNU GPL.

## 0.94 – 0.998 - 2005

Early PHP development versions.
