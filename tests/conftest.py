import pathlib

import pytest

from pi_app.app import config as config_module


@pytest.fixture(autouse=True)
def _temp_config_dir(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_path = config_dir / "config.json"
    monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)
    yield

