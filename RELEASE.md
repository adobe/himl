# Release

1. Install: `pip install bump2version`
2. Bump version: `bump2version minor`
3. Push the release commit: `git push --follow-tags`
4. Wait for Github Actions to finish
   1. A new version is published at https://pypi.org/project/himl/#history
   2. Docker image is published at https://github.com/adobe/himl/pkgs/container/himl
5. Create a new Github release at https://github.com/adobe/himl/releases
