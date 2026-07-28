from fastapi.testclient import TestClient

from solarman_exporter.collector import InverterCollector
from solarman_exporter.config import Settings
from solarman_exporter.main import create_app

from .conftest import sample_profile, write_profile
from .test_collector import FakeClient


def test_http_endpoints_report_liveness_readiness_and_metrics(tmp_path) -> None:
    profile_path = write_profile(tmp_path / "profile.yaml", sample_profile())
    settings = Settings(
        host="192.0.2.10",
        serial=1126866902,
        port=8899,
        slave_id=1,
        poll_interval_seconds=60,
        ready_max_age_seconds=45,
        inverter_name="deye",
        profile_path=profile_path,
        http_host="127.0.0.1",
        http_port=9800,
    )
    collector = InverterCollector(settings, sample_profile(), lambda: FakeClient([1, 5]))
    app = create_app(settings, collector)

    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/ready").status_code == 200
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "solarman_grid_power_watts" in response.text
