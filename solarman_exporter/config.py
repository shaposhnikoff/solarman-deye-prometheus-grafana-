"""Configuration loading for the standalone exporter."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PROFILE_NAME = "deye_hybrid.yaml"


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} must be set")
    return value


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _repository_profile() -> Path:
    source_root = Path(__file__).resolve().parents[1]
    source_profile = source_root / "profiles" / DEFAULT_PROFILE_NAME
    if source_profile.is_file():
        return source_profile
    return Path("/app/profiles") / DEFAULT_PROFILE_NAME


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated exporter configuration sourced from environment variables."""

    host: str
    serial: int
    port: int
    slave_id: int
    poll_interval_seconds: int
    ready_max_age_seconds: int
    inverter_name: str
    profile_path: Path
    http_host: str
    http_port: int

    @classmethod
    def from_environment(cls) -> Settings:
        profile_value = os.getenv("SOLARMAN_PROFILE_PATH")
        profile_path = Path(profile_value) if profile_value else _repository_profile()
        if not profile_path.is_file():
            raise ValueError(f"SOLARMAN_PROFILE_PATH does not exist: {profile_path}")

        poll_interval = _positive_int("SOLARMAN_POLL_INTERVAL_SECONDS", 15)
        return cls(
            host=_required("SOLARMAN_HOST"),
            serial=_positive_int("SOLARMAN_SERIAL", 1),
            port=_positive_int("SOLARMAN_PORT", 8899),
            slave_id=_positive_int("SOLARMAN_SLAVE_ID", 1),
            poll_interval_seconds=poll_interval,
            ready_max_age_seconds=_positive_int(
                "SOLARMAN_READY_MAX_AGE_SECONDS", max(poll_interval * 3, 45)
            ),
            inverter_name=os.getenv("SOLARMAN_INVERTER_NAME", "deye").strip() or "deye",
            profile_path=profile_path,
            http_host=os.getenv("SOLARMAN_HTTP_HOST", "0.0.0.0"),
            http_port=_positive_int("SOLARMAN_HTTP_PORT", 9800),
        )
