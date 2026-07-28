"""Polling implementation for Solarman V5 inverters."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any, Protocol

from pysolarmanv5 import PySolarmanV5

from .config import Settings
from .parser import ParameterParser

LOGGER = logging.getLogger(__name__)
QUERY_ATTEMPTS = 2


class SolarmanClient(Protocol):
    """Minimal client interface used by the collector and tests."""

    def read_holding_registers(self, register_addr: int, quantity: int) -> list[int]: ...

    def read_input_registers(self, register_addr: int, quantity: int) -> list[int]: ...

    def disconnect(self) -> None: ...


@dataclass(frozen=True, slots=True)
class PollStatus:
    """Outcome and freshness metadata for the latest polling attempt."""

    last_success_timestamp: float | None = None
    last_attempt_timestamp: float | None = None
    duration_seconds: float = 0.0
    failures_total: int = 0
    last_error: str | None = None


class InverterCollector:
    """Read all configured register ranges and retain only complete snapshots."""

    def __init__(
        self,
        settings: Settings,
        profile: dict[str, Any],
        client_factory: Callable[[], SolarmanClient] | None = None,
    ) -> None:
        self.settings = settings
        self.profile = profile
        self._client_factory = client_factory or self._make_client
        self._lock = threading.Lock()
        self._snapshot: dict[str, Any] = {}
        self._status = PollStatus()

    def _make_client(self) -> SolarmanClient:
        return PySolarmanV5(
            self.settings.host,
            self.settings.serial,
            port=self.settings.port,
            mb_slave_id=self.settings.slave_id,
            logger=None,
            auto_reconnect=True,
            socket_timeout=15,
        )

    def poll(self) -> bool:
        """Poll every configured request range; return true only for a complete snapshot."""
        with self._lock:
            started = time.monotonic()
            attempted_at = time.time()
            client: SolarmanClient | None = None
            try:
                parser = ParameterParser(self.profile)
                client = self._client_factory()
                for request in self.profile["requests"]:
                    self._read_request(client, parser, request)
                self._snapshot = parser.get_result()
                self._status = replace(
                    self._status,
                    last_success_timestamp=time.time(),
                    last_attempt_timestamp=attempted_at,
                    duration_seconds=time.monotonic() - started,
                    last_error=None,
                )
                LOGGER.info("Solarman polling succeeded with %d values", len(self._snapshot))
                return True
            except Exception as exc:
                self._status = replace(
                    self._status,
                    last_attempt_timestamp=attempted_at,
                    duration_seconds=time.monotonic() - started,
                    failures_total=self._status.failures_total + 1,
                    last_error=f"{type(exc).__name__}: {exc}",
                )
                LOGGER.warning("Solarman polling failed: %s", self._status.last_error)
                return False
            finally:
                if client is not None:
                    try:
                        client.disconnect()
                    except Exception:
                        LOGGER.debug("Solarman disconnect failed", exc_info=True)

    def _read_request(
        self, client: SolarmanClient, parser: ParameterParser, request: dict[str, int]
    ) -> None:
        start = request["start"]
        length = request["end"] - start + 1
        function_code = request["mb_functioncode"]
        last_error: Exception | None = None
        for _ in range(QUERY_ATTEMPTS):
            try:
                if function_code == 3:
                    response = client.read_holding_registers(register_addr=start, quantity=length)
                elif function_code == 4:
                    response = client.read_input_registers(register_addr=start, quantity=length)
                else:
                    raise ValueError(f"unsupported Modbus function code: {function_code}")
                parser.parse(response, start, length)
                return
            except Exception as exc:
                last_error = exc
        register_range = f"{start:#x}-{start + length - 1:#x}"
        raise RuntimeError(f"register range {register_range} failed") from last_error

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._snapshot)

    def status(self) -> PollStatus:
        with self._lock:
            return self._status
