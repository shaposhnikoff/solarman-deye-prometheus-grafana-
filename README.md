# Solarman Deye Prometheus Exporter

Standalone exporter for Deye Hybrid inverters with a Solarman V5 logger. It polls the logger over the local network and exposes the latest complete data set in Prometheus format.

## Quick start

```bash
cp .env.example .env
# Set SOLARMAN_HOST and SOLARMAN_SERIAL for your logger.
./docker-compose.sh up
curl http://localhost:9800/metrics
```

`docker-compose.sh` wraps the project: `check` validates the compose model and
the `.env` file, `build` tags the image `solarman-exporter:local` (the name the
homenet monitoring stack references), `up` builds and starts the container, and
`ps`, `logs` and `down` cover the rest. `up` refuses a foreign container name or
a busy port 9800; on the monitoring host stop `solarman-exporter.service` before
the first container start.

The service exposes:

- `/metrics` — Prometheus metrics
- `/health` — process liveness
- `/ready` — `200` after a fresh successful inverter poll

The default profile is [`profiles/deye_hybrid.yaml`](profiles/deye_hybrid.yaml). It exports numeric inverter fields in Prometheus SI units, along with `solarman_up`, `solarman_data_age_seconds`, `solarman_last_success_timestamp_seconds`, and `solarman_poll_failures_total`. Fields with a lookup table (grid and generator connection, running and battery status, smart-load enable, work mode) publish both the numeric key as `solarman_<field>` and a `solarman_<field>_info` metric carrying the state label.

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

## systemd deployment on the monitoring host

The deployed checkout is `/home/max/solarman-deye-prometheus-grafana-` on `192.168.10.68`.
The unit source is [`deploy/systemd/solarman-exporter.service`](deploy/systemd/solarman-exporter.service);
the installed unit is `/etc/systemd/system/solarman-exporter.service`.
It runs the local `.venv/bin/solarman-exporter` as user `max`, and the application loads
the ignored `.env` file from the checkout. Do not commit or print that file.

Install or refresh the unit after reviewing changes:

```bash
sudo install -m 0644 deploy/systemd/solarman-exporter.service /etc/systemd/system/
sudo systemd-analyze verify /etc/systemd/system/solarman-exporter.service
sudo systemctl daemon-reload
sudo systemctl enable --now solarman-exporter.service
```

Check `systemctl status solarman-exporter.service`,
`journalctl -u solarman-exporter.service -n 50 --no-pager`,
`curl http://192.168.10.68:9800/ready`, and Prometheus job `deye`.
The old Supervisor program `solarman` has autostart and autorestart disabled;
keep it stopped while the systemd unit is active.

The Modbus RTU exporter is a different project:
[`deye-6-modbus-management`](https://github.com/shaposhnikoff/deye-6-modbus-management).
It runs on `192.168.10.39:9101` as `deye-monitoring.service` and is scraped
by the separate Prometheus job `deye-modbus`.
