import importlib.util
import io
import json
import runpy
from pathlib import Path
from urllib.error import URLError
from unittest.mock import patch

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "python_versions.py"


@pytest.fixture
def discovery():
    spec = importlib.util.spec_from_file_location("python_versions", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_selects_supported_stable_versions_in_numeric_order(discovery):
    data = {
        "3.9": {"status": "security"},
        "3.16": {"status": "feature"},
        "3.15": {"status": "bugfix"},
        "3.14": {"status": "prerelease"},
        "3.10": {"status": "end-of-life"},
        "3.11": {"status": "security"},
    }

    assert discovery.supported_versions(data) == ["3.9", "3.11", "3.15"]


@pytest.mark.parametrize(
    "data",
    [
        [],
        {},
        {"3.10": {"status": "end-of-life"}},
        {"3.15": None},
        {"3.15": {}},
        {"main": {"status": "bugfix"}},
    ],
)
def test_rejects_malformed_or_empty_supported_versions(discovery, data):
    with pytest.raises(ValueError):
        discovery.supported_versions(data)


def test_retries_a_transient_fetch_failure(discovery):
    response = io.BytesIO(b'{"3.15": {"status": "bugfix"}}')
    with patch.object(discovery, "urlopen", side_effect=[URLError("unavailable"), response]):
        with patch.object(discovery.time, "sleep"):
            assert discovery.fetch_versions() == ["3.15"]


def test_stops_after_three_failed_fetches(discovery):
    with patch.object(
        discovery, "urlopen", side_effect=[URLError("unavailable")] * 3 + [AssertionError("too many attempts")]
    ):
        with patch.object(discovery.time, "sleep"):
            with pytest.raises(RuntimeError, match="retrieve supported Python versions"):
                discovery.fetch_versions()


def test_does_not_retry_invalid_json(discovery):
    with patch.object(discovery, "urlopen", side_effect=[io.BytesIO(b"not JSON"), AssertionError("unexpected retry")]):
        with pytest.raises(ValueError):
            discovery.fetch_versions()


def test_emits_matrix_and_latest_version_for_github_actions(capsys):
    response = io.BytesIO(b'{"3.15": {"status": "bugfix"}, "3.11": {"status": "security"}}')
    with patch("urllib.request.urlopen", return_value=response):
        runpy.run_path(str(SCRIPT), run_name="__main__")

    outputs = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert json.loads(outputs["versions"]) == ["3.11", "3.15"]
    assert outputs["latest"] == "3.15"
