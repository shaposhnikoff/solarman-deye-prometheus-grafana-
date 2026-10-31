from prometheus_client import generate_latest

from solarman_exporter.collector import PollStatus
from solarman_exporter.metrics import PrometheusMetrics

from .conftest import sample_profile

SERIAL = "1126866902"


def series(name: str) -> str:
    return f'{name}{{inverter="deye",serial="{SERIAL}"}}'


def info(name: str, state: str) -> str:
    return f'{name}{{inverter="deye",serial="{SERIAL}",state="{state}"}}'


def test_metrics_use_si_units_and_publish_lookup_states() -> None:
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
    assert f"{series('solarman_battery_status')} 65535.0" in exposition
    assert f"{info('solarman_battery_status_info', 'Charge')} 1.0" in exposition


def test_lookup_state_switches_off_the_previous_value() -> None:
    metrics = PrometheusMetrics(sample_profile(), 1126866902, "deye")
    status = PollStatus(last_success_timestamp=1.0, last_attempt_timestamp=1.0)

    metrics.update({"Grid-connected Status": "On-Grid"}, status, successful=True)
    exposition = generate_latest(metrics.registry).decode()
    assert f"{series('solarman_grid_connected_status')} 1.0" in exposition
    assert f"{info('solarman_grid_connected_status_info', 'On-Grid')} 1.0" in exposition

    metrics.update({"Grid-connected Status": "Off-Grid"}, status, successful=True)
    exposition = generate_latest(metrics.registry).decode()
    assert f"{series('solarman_grid_connected_status')} 0.0" in exposition
    assert f"{info('solarman_grid_connected_status_info', 'On-Grid')} 0.0" in exposition
    assert f"{info('solarman_grid_connected_status_info', 'Off-Grid')} 1.0" in exposition


def test_unknown_lookup_label_is_ignored() -> None:
    metrics = PrometheusMetrics(sample_profile(), 1126866902, "deye")
    status = PollStatus(last_success_timestamp=1.0, last_attempt_timestamp=1.0)

    metrics.update({"Grid-connected Status": "Islanded"}, status, successful=True)
    exposition = generate_latest(metrics.registry).decode()

    assert "solarman_grid_connected_status{" not in exposition
    assert "solarman_grid_connected_status_info{" not in exposition
