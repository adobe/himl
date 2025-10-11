# Release Process

This project uses [bump-my-version](https://github.com/callowayproject/bump-my-version) for automated version management and releases.

## Prerequisites

1. Ensure you have the development dependencies installed:
   ```bash
   pip install -e .[dev]
   ```

2. Ensure your working directory is clean (all changes committed)

3. Ensure you're on the `main` branch and up to date:
   ```bash
   git checkout main
   git pull origin main
   ```

## Release Steps

### 1. Choose Version Type

Determine the type of release based on the changes:
- **Patch** (`0.16.4 → 0.16.5`): Bug fixes, documentation updates
- **Minor** (`0.16.4 → 0.17.0`): New features, backward-compatible changes
- **Major** (`0.16.4 → 1.0.0`): Breaking changes

### 2. Preview the Release

Check what the version bump would do:
```bash
# See all possible version bumps
make show-bump

# Dry run the specific bump you want to make
make dry-bump-patch   # For patch releases
make dry-bump-minor   # For minor releases
make dry-bump-major   # For major releases
```

### 3. Execute the Version Bump

Run the appropriate bump command:
```bash
make bump-patch   # For patch releases
make bump-minor   # For minor releases
make bump-major   # For major releases
```

This will automatically:
- Update the version in `pyproject.toml`
- Update the version in `README.md`
- Update the version in `himl/main.py` (CLI help)
- Create a Git commit with message `[RELEASE] - Release version X.Y.Z`
- Create a Git tag `X.Y.Z`

### 4. Push the Release

Push the commit and tags to trigger the release:
```bash
git push --follow-tags
```

### 5. Monitor Automated Release

Wait for GitHub Actions to complete:
1. **PyPI Release**: A new version will be published at https://pypi.org/project/himl/#history
2. **Docker Image**: Published at https://github.com/adobe/himl/pkgs/container/himl
3. **GitHub Release**: Automatically created at https://github.com/adobe/himl/releases

### 6. Verify Release

1. Check that the new version appears on PyPI
2. Verify the Docker image is available
3. Test install the new version: `pip install himl==X.Y.Z`
4. Update the GitHub release notes if needed

