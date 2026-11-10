# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release.
- Token-count estimation for literal text, files, stdin and whole directories.
- Two offline estimation methods: `heuristic` (default) and `chars`.
- Configurable price table with shipped placeholder defaults, overridable via
  `--pricing FILE` or the `TOKENCOST_PRICING` environment variable.
- Cost estimation per model with optional assumed output tokens.
- Repo mode with `.gitignore` support and `--include`/`--exclude` globs.
- `--json` output with a stable schema, `--by-file` breakdown, `--list-models`.
- Exit codes: `0` success, `1` runtime error, `2` usage error.
- GitHub Actions CI on Python 3.10–3.13.

[Unreleased]: https://github.com/vvs1off/tokencost/commits/main
