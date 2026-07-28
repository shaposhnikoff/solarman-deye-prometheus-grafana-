from pathlib import Path

from solarman_exporter.config import Settings


def test_settings_read_logger_serial_from_environment(monkeypatch, tmp_path) -> None:
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text("requests: []\nparameters: []\n", encoding="utf-8")
    monkeypatch.setenv("SOLARMAN_HOST", "192.0.2.10")
    monkeypatch.setenv("SOLARMAN_SERIAL", "1126866902")
    monkeypatch.setenv("SOLARMAN_PROFILE_PATH", str(profile_path))

    settings = Settings.from_environment()

    assert settings.serial == 1126866902
    assert settings.profile_path == Path(profile_path)
