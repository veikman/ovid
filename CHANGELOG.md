# Change log
This log follows the conventions of
[keepachangelog.com](http://keepachangelog.com/). It picks up from Ovid
version 0.5.0.

## [Unreleased]
### Changed
- Modernized use of `setuptools` (via PyPA `build`) for PyPI publication.
    - Removed Debian system packaging shortcuts.
- Converted unit tests to `pytest`.

### Added
- Flake8 configuration via `pyproject.toml`, hence via `pflake8`.

### Fixed
- Linting.

## [0.5.1] - 2020-10-24
### Changed
- Switched from `distutils.core` to `setuptools` to enable wheel distribution.
- Changed distribution name from `Ovid` to `ovid`.

[Unreleased]: https://github.com/veikman/ovid/compare/ovid-v0.5.1...HEAD
[0.5.1]: https://github.com/veikman/ovid/compare/ovid-v0.5.0...v0.5.1
