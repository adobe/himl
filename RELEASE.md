# Release Process

This project uses [bump-my-version](https://github.com/callowayproject/bump-my-version)
to update release versions and setuptools_scm to derive package versions from Git
tags. Prepare and merge a release PR before pushing a release tag. Pushing a tag
publishes to PyPI and GHCR; opening or merging the PR does not publish a release.

## Prerequisites

1. Use Python 3.11 or newer and install the development dependencies in a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -e '.[dev]'
   ```

2. Ensure your working directory is clean (all changes committed)

3. Ensure you're on the `main` branch and up to date:
   ```bash
   git checkout main
   git pull --ff-only origin main
   git fetch origin --tags
   ```

## Release Steps

### 1. Choose Version Type

Review changes since the latest published release and choose the next unused
version. Do not rely only on `tool.bumpversion.current_version`: older releases
may have been tagged without updating it.

- **Patch**: Bug fixes and documentation updates
- **Minor**: New features and backward-compatible changes
- **Major**: Breaking changes for stable releases

While the project is pre-1.0, breaking changes may ship in a minor release, but
must be called out with migration guidance. Release 0.23.0 requires Python 3.11+
and changes merge behavior; see [README.md](README.md#release-0230).

### 2. Prepare the Release PR

Replace `X.Y.Z` with the chosen version in the commands below:
```bash
git checkout -b release/X.Y.Z
bump-my-version bump --new-version X.Y.Z --no-commit --no-tag --dry-run
bump-my-version bump --new-version X.Y.Z --no-commit --no-tag
```

This updates:
- `tool.bumpversion.current_version` in `pyproject.toml`
- The latest version in `README.md`
- The CLI version in `himl/main.py`

Update the README release notes, including breaking changes, migration guidance,
and a comparison link from the previous release. Do not edit the generated
`himl/_version.py`; setuptools_scm generates it from Git metadata.

The `make bump-*` shortcuts create a commit and tag automatically. Do not use
them for a release PR, and do not push tags before the PR is merged.

### 3. Validate and Open the PR

Run the same core checks as CI:
```bash
make lint
python -m pytest tests/ -v --tb=short --cov=himl --cov-report=term-missing --cov-fail-under=80
python -m build
python -m twine check dist/*
himl --version
himl --help
himl-config-merger --help
himl examples/simple/production --format yaml
```

Before tagging, package metadata will contain a development version even though
`himl --version` reports the prepared release version. To validate release
artifacts without creating a tag, build with
`SETUPTOOLS_SCM_PRETEND_VERSION=X.Y.Z python -m build` and inspect the resulting
wheel and source distribution.

Commit the release files, push only the branch, and open a PR using
`.github/pull_request_template.md`. Include the exact validation commands and
their results. Wait for CI and review before merging.

### 4. Tag the Merged Release

After the release PR is merged, update `main`, verify the release versions and
CI results, then tag the reviewed release commit:
```bash
git checkout main
git pull --ff-only origin main
git tag -a X.Y.Z -m "Release X.Y.Z"
git push origin X.Y.Z
```

Push only the intended release tag, not all local tags.

### 5. Monitor Automated Release

Wait for GitHub Actions to complete:
1. **PyPI Release**: A new version will be published at https://pypi.org/project/himl/#history
2. **Docker Image**: Published at https://github.com/adobe/himl/pkgs/container/himl

The publishing workflows do not create a GitHub Release. Create it from the
pushed tag, then review the generated notes and add the README migration guidance:
```bash
gh release create X.Y.Z --verify-tag --title "Release X.Y.Z" --generate-notes
```

### 6. Verify Release

1. Check that the new version appears on PyPI
2. Verify the Docker image is available
3. Test install the new version: `pip install himl==X.Y.Z`
4. Verify the GitHub release notes include breaking changes and migration guidance
