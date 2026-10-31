"""Prometheus metric registration and unit conversion."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

from prometheus_client import CollectorRegistry, Gauge

from .collector import PollStatus

UNIT_CONVERSIONS: dict[str, tuple[str, float]] = {
    "W": ("watts", 1.0),
    "kW": ("watts", 1_000.0),
    "V": ("volts", 1.0),
    "A": ("amperes", 1.0),
    "%": ("ratio", 0.01),
    "°C": ("celsius", 1.0),
    "Hz": ("hertz", 1.0),
    "Wh": ("joules", 3_600.0),
    "kWh": ("joules", 3_600_000.0),
    "VA": ("volt_amperes", 1.0),
    "VAR": ("volt_amperes_reactive", 1.0),
    "kVar": ("volt_amperes_reactive", 1_000.0),
    "s": ("seconds", 1.0),
    "min": ("seconds", 60.0),
    "h": ("seconds", 3_600.0),
}


def normalize_metric_name(value: str) -> str:
    """Convert a profile field name into a stable Prometheus metric fragment."""
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return re.sub(r"_+", "_", normalized)


@dataclass(frozen=True, slots=True)
class MetricSpec:
    """A numeric profile field and its Prometheus representation."""

    field_name: str
    metric_name: str
    conversion_factor: float
    description: str


def metric_specs(profile: dict[str, Any]) -> list[MetricSpec]:
    """Derive numeric metric definitions from a Solarman YAML profile."""
    specs: list[MetricSpec] = []
    names: set[str] = set()
    for group in profile["parameters"]:
        for field in group["items"]:
            if field["rule"] not in {1, 2, 3, 4} or field.get("isstr") or "lookup" in field:
                continue
            suffix, factor = UNIT_CONVERSIONS.get(field.get("uom", ""), ("", 1.0))
            name = f"solarman_{normalize_metric_name(field['name'])}"
            if suffix and not name.endswith(f"_{suffix}"):
                name = f"{name}_{suffix}"
            if "total" in normalize_metric_name(field["name"]).split("_") and not name.endswith(
                "_total"
            ):
                name = f"{name}_total"
            if name in names:
                raise ValueError(f"duplicate Prometheus metric name generated: {name}")
            names.add(name)
            specs.append(
                MetricSpec(
                    field_name=field["name"],
                    metric_name=name,
                    conversion_factor=factor,
                    description=f"Solarman {field['name']} ({field.get('uom', 'raw')})",
                )
            )
    return specs


@dataclass(frozen=True, slots=True)
class StatusSpec:
    """A lookup profile field and its numeric and labelled representations."""

    field_name: str
    metric_name: str
    info_metric_name: str
    key_by_label: dict[str, int]
    description: str


def status_specs(profile: dict[str, Any]) -> list[StatusSpec]:
    """Derive metrics for profile fields that map register keys to labels."""
    specs: list[StatusSpec] = []
    names: set[str] = set()
    for group in profile["parameters"]:
        for field in group["items"]:
            if "lookup" not in field or field["rule"] not in {1, 2, 3, 4}:
                continue
            base = f"solarman_{normalize_metric_name(field['name'])}"
            info_name = f"{base}_info"
            if base in names or info_name in names:
                raise ValueError(f"duplicate Prometheus status metric name generated: {base}")
            names.update({base, info_name})
            key_by_label = {str(option["value"]): int(option["key"]) for option in field["lookup"]}
            specs.append(
                StatusSpec(
                    field_name=field["name"],
                    metric_name=base,
                    info_metric_name=info_name,
                    key_by_label=key_by_label,
                    description=f"Solarman {field['name']}",
                )
            )
    return specs


class PrometheusMetrics:
    """Store the last complete Solarman snapshot in a private Prometheus registry."""

    def __init__(self, profile: dict[str, Any], serial: int, inverter_name: str) -> None:
        self.registry = CollectorRegistry(auto_describe=True)
        self._label_values = {"serial": str(serial), "inverter": inverter_name}
        self._specs = metric_specs(profile)
        self._statuses = status_specs(profile)
        numeric_names = {spec.metric_name for spec in self._specs}
        for spec in self._statuses:
            if spec.metric_name in numeric_names or spec.info_metric_name in numeric_names:
                raise ValueError(
                    f"status metric collides with a numeric metric: {spec.metric_name}"
                )
        self._values = {
            spec.field_name: Gauge(
                spec.metric_name,
                spec.description,
                labelnames=("serial", "inverter"),
                registry=self.registry,
            )
            for spec in self._specs
        }
        self._status_values = {
            spec.field_name: Gauge(
                spec.metric_name,
                f"{spec.description} key",
                labelnames=("serial", "inverter"),
                registry=self.registry,
            )
            for spec in self._statuses
        }
        self._status_info = {
            spec.field_name: Gauge(
                spec.info_metric_name,
                f"{spec.description} state",
                labelnames=("serial", "inverter", "state"),
                registry=self.registry,
            )
            for spec in self._statuses
        }
        self._active_states: dict[str, str] = {}
        self._up = self._gauge("solarman_up", "Whether the last Solarman poll succeeded")
        self._last_success = self._gauge(
            "solarman_last_success_timestamp_seconds", "Unix timestamp of the last successful poll"
        )
        self._last_attempt = self._gauge(
            "solarman_last_attempt_timestamp_seconds", "Unix timestamp of the last polling attempt"
        )
        self._duration = self._gauge(
            "solarman_poll_duration_seconds", "Duration of the latest Solarman polling attempt"
        )
        self._failures = self._gauge(
            "solarman_poll_failures_total", "Number of failed polling attempts"
        )
        self._age = self._gauge(
            "solarman_data_age_seconds", "Age of the last successful data snapshot"
        )
        self._status = PollStatus()

    def _gauge(self, name: str, description: str) -> Gauge:
        return Gauge(name, description, labelnames=("serial", "inverter"), registry=self.registry)

    def update(self, values: dict[str, Any], status: PollStatus, successful: bool) -> None:
        """Publish a new status and replace value samples only after complete polls."""
        self._status = status
        if successful:
            for spec in self._specs:
                value = values.get(spec.field_name)
                if isinstance(value, int | float):
                    self._values[spec.field_name].labels(**self._label_values).set(
                        value * spec.conversion_factor
                    )
            for spec in self._statuses:
                label = values.get(spec.field_name)
                if not isinstance(label, str):
                    continue
                key = spec.key_by_label.get(label)
                if key is None:
                    continue
                self._status_values[spec.field_name].labels(**self._label_values).set(key)
                info = self._status_info[spec.field_name]
                previous = self._active_states.get(spec.field_name)
                if previous is not None and previous != label:
                    info.labels(**self._label_values, state=previous).set(0)
                info.labels(**self._label_values, state=label).set(1)
                self._active_states[spec.field_name] = label
        self._up.labels(**self._label_values).set(1 if successful else 0)
        self._duration.labels(**self._label_values).set(status.duration_seconds)
        self._failures.labels(**self._label_values).set(status.failures_total)
        if status.last_success_timestamp is not None:
            self._last_success.labels(**self._label_values).set(status.last_success_timestamp)
            age_seconds = max(0.0, time.time() - status.last_success_timestamp)
            self._age.labels(**self._label_values).set(age_seconds)
        if status.last_attempt_timestamp is not None:
            self._last_attempt.labels(**self._label_values).set(status.last_attempt_timestamp)

    def is_ready(self, maximum_age_seconds: int) -> bool:
        return (
            self._status.last_success_timestamp is not None
            and time.time() - self._status.last_success_timestamp <= maximum_age_seconds
        )

    @property
    def status(self) -> PollStatus:
        return self._status
