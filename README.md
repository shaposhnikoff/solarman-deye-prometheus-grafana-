# Solarman Deye Prometheus Exporter

Standalone exporter for Deye Hybrid inverters with a Solarman V5 logger. It polls the logger over the local network and exposes the latest complete data set in Prometheus format.

## Quick start

```bash
cp .env.example .env
# Set SOLARMAN_HOST and SOLARMAN_SERIAL for your logger.
docker compose up --build -d
curl http://localhost:9800/metrics
```

The service exposes:

- `/metrics` — Prometheus metrics
- `/health` — process liveness
- `/ready` — `200` after a fresh successful inverter poll

The default profile is [`profiles/deye_hybrid.yaml`](profiles/deye_hybrid.yaml). It exports numeric inverter fields in Prometheus SI units, along with `solarman_up`, `solarman_data_age_seconds`, `solarman_last_success_timestamp_seconds`, and `solarman_poll_failures_total`.

## Prometheus

```yaml
scrape_configs:
  - job_name: solarman
    static_configs:
      - targets: ["solarman-exporter:9800"]
```

## Grafana

Import [`grafana/solarman-overview.json`](grafana/solarman-overview.json) and choose the Prometheus datasource. The dashboard covers solar generation, grid and load power, battery state, daily energy, and exporter health.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `SOLARMAN_HOST` | required | Logger IP address or hostname |
| `SOLARMAN_SERIAL` | required | Logger serial number |
| `SOLARMAN_PORT` | `8899` | Logger TCP port |
| `SOLARMAN_SLAVE_ID` | `1` | Modbus slave ID |
| `SOLARMAN_POLL_INTERVAL_SECONDS` | `15` | Polling interval |
| `SOLARMAN_READY_MAX_AGE_SECONDS` | `45` | Maximum age of data for readiness |
| `SOLARMAN_PROFILE_PATH` | bundled profile | Absolute path to another compatible profile |
