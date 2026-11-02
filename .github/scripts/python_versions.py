"""Discover supported stable releases from the Python Developer's Guide data."""

import json
import re
import time
from urllib.request import urlopen


def supported_versions(data: dict) -> list[str]:
    if not isinstance(data, dict):
        raise ValueError("Expected a release-cycle JSON object")

    versions = []
    for version, details in data.items():
        if not isinstance(details, dict) or not isinstance(details.get("status"), str):
            raise ValueError(f"Invalid release-cycle entry: {version}")
        if details["status"] in {"bugfix", "security"}:
            if not re.fullmatch(r"3\.\d+", version):
                raise ValueError(f"Invalid supported Python version: {version}")
            versions.append(version)

    if not versions:
        raise ValueError("No supported stable Python versions found")
    return sorted(versions, key=lambda version: tuple(map(int, version.split("."))))


def fetch_versions() -> list[str]:
    for attempt in range(3):
        try:
            with urlopen("https://peps.python.org/api/release-cycle.json", timeout=15) as response:
                data = json.load(response)
            break
        except OSError as error:
            if attempt == 2:
                raise RuntimeError("Unable to retrieve supported Python versions after 3 attempts") from error
            time.sleep(attempt + 1)

    return supported_versions(data)


if __name__ == "__main__":
    versions = fetch_versions()
    print(f"versions={json.dumps(versions)}")
    print(f"latest={versions[-1]}")
