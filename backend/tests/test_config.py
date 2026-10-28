from pathlib import Path

from app.config import BACKEND_ENV_FILE


def test_environment_file_is_resolved_relative_to_backend_package():
    assert BACKEND_ENV_FILE == Path(__file__).resolve().parents[1] / ".env"
