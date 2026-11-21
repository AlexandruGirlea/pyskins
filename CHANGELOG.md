# Changelog

## 0.1.2 (2026-11-21)

- Small wording changes in the README and the skill file. No code changes.

## 0.1.1 (2026-11-21)

- `pyskins run` takes `-s` as a short form of `--skin`, like the other commands.
- `pyskins add` shows the right next steps after you add an obfuscation key.
- README: the buttons at the top now work on PyPI too. It also has badges, a table of the Python functions, the folders that folder obfuscation skips, and `apm install … --target`.
- The tests run on Python 3.8 through 3.15, on Linux and macOS, and against the installed package.
- A new skin file needs no change to the tests.
- The code uses f-strings and plain `str`, and the linter keeps it that way.
- Package metadata: SPDX licence, one classifier for each Python version, links to the changelog and the demo.
- New: `SECURITY.md`, `CODE_OF_CONDUCT.md`, and templates for issues and pull requests.

## 0.1.0 (2026-11-21)

First release.

- The skins `christmas` and `faces`.
- The `pyskins` command: `list`, `show`, `apply`, `undo`, `run`, `new`, `check`, `add` and `obfuscate`.
- The start-up hook that lets plain `python` run skinned files.
