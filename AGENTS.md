# AGENTS.md

Instructions for AI coding agents (Claude Code, Codex, GitHub Copilot) working in this repository.
`CLAUDE.md` is a symlink to this file; edit `AGENTS.md` only.

## Project overview

OIOIOI is the Django web frontend of the SIO2 contest system.

- `oioioi/`: the main package, one Django app per subdirectory (`contests`, `problems`, `evalmgr`, `sinolpack`, ...).
- `oioioi/default_settings.py`: base settings. `oioioi/test_settings.py`: settings for unit tests (selected in `pytest.ini`).
- `oioioi_cypress/`: Cypress end-to-end tests. `rst/`: Sphinx docs.
- Python 3.13, dependencies managed with `uv` (`pyproject.toml`, `uv.lock`). JS dependencies managed with `pnpm` (`package.json`, `pnpm-lock.yaml`), bundled with webpack.

## Dev environment

- **Docker** (the supported setup): `./easy_toolbox.py build`, `./easy_toolbox.py up`, `./easy_toolbox.py run`, `./easy_toolbox.py test` (`./easy_toolbox.py -h` lists all commands).
  Raw equivalent: `OIOIOI_UID=$(id -u) docker compose -f docker-compose-dev.yml ...`. Set `OIOIOI_UID` so files created in the bind-mounted checkout belong to you.
- **Native** (fast edit-test loop): `uv sync` (the `dev` group is installed by default), then `./test.sh`. On macOS follow "Running tests on macOS (Homebrew)" in `INSTALL.rst`.
- Windows is not supported.

## Commands

- Tests (pytest, run from the repo root):
  - `./test.sh [path[::Class[::test]]] [-n auto] [-x]`: e.g. `./test.sh -n auto oioioi/contests`.
  - `tox -- [path] [pytest args]`: the same in an isolated environment (arguments must come after `--`).
  - In Docker: `docker compose -f docker-compose-dev.yml exec web ../oioioi/test.sh [path]`.
  - Tests marked `@pytest.mark.slow` are skipped unless you pass `--runslow` (the nightly build runs them).
  - Decorate Linux-only tests with `needs_linux` from `oioioi.base.tests`; they are skipped on other systems. The bare `pytest.mark.needs_linux` marker does not skip anything.
  - CI runs `./test.sh -n auto --migrations`.
- Python lint and format: `ruff check . --fix && ruff format .`.
- JS lint: `pnpm run lint` (ESLint).
- JS build: `pnpm install --frozen-lockfile && pnpm run build` (output in `dist_webpack/`). Use plain `pnpm install` / `pnpm add` only when changing dependencies.

## Code style

- Python line length is **160**. Ruff rules: `E`, `W`, `F`, `I`, `B`, `UP`, `C4`, minus `B904`, `B026`, `C416`; target `py313` (see `[tool.ruff]` in `pyproject.toml`).
- Ruff excludes `migrations/`, `oioioi/**/*settings.py` and a few other files (see `exclude` in `[tool.ruff]`); don't reformat them.
- ESLint uses the flat config `eslint.config.mjs` and only checks `oioioi/**/*.js`. `$`, `jQuery`, `Cookies`, `Highcharts`, `django`, `gettext`, `ngettext`, `interpolate` and `oioioi_base_url` are globals; don't import them.
- User-facing strings go through Django's translation functions (`gettext_lazy as _` etc.).

## Gotchas

- `DEFAULT_AUTO_FIELD` must stay `django.db.models.AutoField` (32-bit ids). Changing it would generate migrations for every model.
- Tests use `oioioi.test_settings`, not `default_settings`, and run with `--nomigrations` (both set in `pytest.ini`). Pass `--migrations` to check that migrations apply, as CI does.
- `DeprecationWarning`, `PendingDeprecationWarning` and `RuntimeWarning` raised from `oioioi` code are errors in tests.
- Building `bsddb3` (pulled in by filetracker) needs Berkeley DB (`libdb-dev` on Debian/Ubuntu, `berkeley-db@5` on macOS plus `BERKELEYDB_DIR`) and `YES_I_HAVE_THE_RIGHT_TO_USE_THIS_BERKELEY_DB_VERSION=1`.
- pre-commit and CI run `ruff check --fix --exit-non-zero-on-fix`, so a file that ruff had to fix still fails the check. Commit the fixes.
- CI pins ruff 0.15.1 (`.github/workflows/ruff.yml`, `.pre-commit-config.yaml`), while the `dev` group pins an older one. To match CI, use `pre-commit run --all-files` or `uvx ruff@0.15.1`.
- The Docker build runs `pnpm install --frozen-lockfile`: commit `pnpm-lock.yaml` together with any `package.json` change. Likewise commit `uv.lock` with `pyproject.toml` changes. CI checks both lockfiles.
- Translations (`oioioi/_locale/locale/*/LC_MESSAGES/*.po`) are synced with Transifex by GitHub workflows. Change English strings in the source code and don't hand-edit other languages.

## Workflow

- Work on a feature branch and open a PR against `master`.
- Before opening a PR, run ruff and the tests for the apps you touched.
- When you change models, add a migration (`./manage.py makemigrations <app>`, e.g. via `./easy_toolbox.py exec python manage.py makemigrations <app>`) and commit it.
- Keep local notes, reports and context files in `internal/`, and personal Claude Code instructions in `CLAUDE.local.md`. Both are ignored by git and Docker.
