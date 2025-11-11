from pi_app.app.config import ConfigData, load_config, save_config


def test_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("pi_app.app.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("pi_app.app.config.CONFIG_PATH", tmp_path / "config.json")

    data = ConfigData(
        camera_type="seek",
        palette_index=5,
        threshold_c=42.5,
        threshold_mode="<",
        auto_exposure_lock=True,
        ffc_path="/tmp/ffc.png",
        temperature_unit="F",
        default_threshold_c=35.0,
        default_threshold_f=95.0,
    )
    save_config(data)
    loaded = load_config()

    assert loaded == data

