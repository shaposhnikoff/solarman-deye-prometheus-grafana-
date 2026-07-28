from prometheus_client import generate_latest

from solarman_exporter.collector import PollStatus
from solarman_exporter.metrics import PrometheusMetrics

from .conftest import sample_profile


def test_metrics_use_si_units_and_exclude_string_fields() -> None:
    metrics = PrometheusMetrics(sample_profile(), 1126866902, "deye")
    status = PollStatus(last_success_timestamp=1.0, last_attempt_timestamp=1.0)

    metrics.update(
        {"Grid Power": -1, "Total Production": 5, "Battery SOC": 51, "Battery Status": "Charge"},
        status,
        successful=True,
    )
    exposition = generate_latest(metrics.registry).decode()

    assert "solarman_grid_power_watts" in exposition
    assert "solarman_total_production_joules_total" in exposition
    assert "1.8e+07" in exposition
    assert "solarman_battery_soc_ratio" in exposition
    assert "0.51" in exposition
    assert "battery_status" not in exposition
