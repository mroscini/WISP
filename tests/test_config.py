from __future__ import annotations

import pytest

from wisp.config import ConfigError, ConfigStore


def test_config_is_created_atomically_from_defaults(tmp_path):
    path = tmp_path / "config.json"
    store = ConfigStore(path)
    config = store.ensure()
    assert path.exists()
    assert config["active_character_id"] == "spider-man"
    assert config["characters"][0]["name"] == "Spider-Man"


def test_active_character_must_exist(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    config = store.defaults()
    config["active_character_id"] = "missing"
    with pytest.raises(ConfigError, match="active_character_id"):
        store.save(config)


def test_duplicate_character_ids_are_rejected(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    config = store.defaults()
    config["characters"].append(dict(config["characters"][0]))
    with pytest.raises(ConfigError, match="unique"):
        store.save(config)


def test_invalid_button_gpio_is_rejected(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    config = store.defaults()
    config["button"]["line"] = -1
    with pytest.raises(ConfigError, match="GPIO"):
        store.save(config)

