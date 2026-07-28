from __future__ import annotations

from pathlib import Path

from solarman_exporter.collector import InverterCollector
from solarman_exporter.config import Settings

from .conftest import sample_profile


class FakeClient:
    def __init__(self, response: list[int] | Exception) -> None:
        self.response = response
        self.read_count = 0
        self.disconnected = False

    def read_holding_registers(self, register_addr: int, quantity: int) -> list[int]:
        self.read_count += 1
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    def read_input_registers(self, register_addr: int, quantity: int) -> list[int]:
        return self.read_holding_registers(register_addr, quantity)

    def disconnect(self) -> None:
        self.disconnected = True


def settings() -> Settings:
    return Settings(
        host="192.0.2.10",
        serial=1126866902,
        port=8899,
        slave_id=1,
        poll_interval_seconds=15,
        ready_max_age_seconds=45,
        inverter_name="deye",
        profile_path=Path("profile.yaml"),
        http_host="127.0.0.1",
        http_port=9800,
    )


def test_collector_keeps_last_complete_snapshot_after_failure() -> None:
    clients = iter([FakeClient([0xFFFF, 5]), FakeClient(ConnectionError("offline"))])

    def factory() -> FakeClient:
        return next(clients)

    collector = InverterCollector(settings(), sample_profile(), client_factory=factory)

    assert collector.poll() is True
    successful_snapshot = collector.snapshot()
    assert successful_snapshot["Grid Power"] == -1

    assert collector.poll() is False
    assert collector.snapshot() == successful_snapshot
    assert collector.status().failures_total == 1
