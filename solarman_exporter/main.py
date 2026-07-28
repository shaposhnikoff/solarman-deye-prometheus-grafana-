"""ASGI entry point for the Solarman Prometheus exporter."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
import yaml
from fastapi import FastAPI, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .collector import InverterCollector
from .config import Settings
from .metrics import PrometheusMetrics

LOGGER = logging.getLogger(__name__)


def load_profile(path: Path) -> dict:
    """Load and minimally validate an inverter register profile."""
    with path.open(encoding="utf-8") as profile_file:
        profile = yaml.safe_load(profile_file)
    if not isinstance(profile, dict) or not {"requests", "parameters"} <= profile.keys():
        raise ValueError(f"invalid Solarman profile: {path}")
    return profile


async def run_poller(
    collector: InverterCollector,
    metrics: PrometheusMetrics,
    stop_event: asyncio.Event,
) -> None:
    """Run serial polls until FastAPI begins shutdown."""
    while not stop_event.is_set():
        successful = await asyncio.to_thread(collector.poll)
        metrics.update(collector.snapshot(), collector.status(), successful)
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=collector.settings.poll_interval_seconds
            )
        except TimeoutError:
            pass


def create_app(settings: Settings, collector: InverterCollector | None = None) -> FastAPI:
    """Create the exporter application and its polling lifecycle."""
    profile = load_profile(settings.profile_path)
    active_collector = collector or InverterCollector(settings, profile)
    metrics = PrometheusMetrics(profile, settings.serial, settings.inverter_name)
    stop_event = asyncio.Event()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        poll_task = asyncio.create_task(run_poller(active_collector, metrics, stop_event))
        try:
            yield
        finally:
            stop_event.set()
            poll_task.cancel()
            try:
                await poll_task
            except asyncio.CancelledError:
                pass

    app = FastAPI(
        title="Solarman Prometheus Exporter",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.metrics = metrics

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    def ready() -> dict[str, str]:
        if not metrics.is_ready(settings.ready_max_age_seconds):
            return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        return {"status": "ready"}

    @app.get("/metrics", include_in_schema=False)
    def prometheus_metrics() -> Response:
        return Response(generate_latest(metrics.registry), media_type=CONTENT_TYPE_LATEST)

    return app


def main() -> None:
    """Launch the exporter using configuration from environment variables."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = Settings.from_environment()
    uvicorn.run(
        create_app(settings),
        host=settings.http_host,
        port=settings.http_port,
        log_level="info",
    )
