"""YAML register profile parsing independent of Home Assistant."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


class ParameterParser:
    """Decode Solarman register responses using an inverter YAML profile."""

    def __init__(self, profile: dict[str, Any]) -> None:
        self._profile = profile
        self._result: dict[str, Any] = {}

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return [item for group in self._profile["parameters"] for item in group["items"]]

    def parse(self, raw_data: Iterable[int], start: int, length: int) -> None:
        registers = list(raw_data)
        if len(registers) != length:
            raise ValueError(f"expected {length} registers, received {len(registers)}")
        for definition in self.definitions:
            self._parse_field(registers, definition, start, length)

    def get_result(self) -> dict[str, Any]:
        return dict(self._result)

    def _parse_field(
        self, raw_data: list[int], definition: dict[str, Any], start: int, length: int
    ) -> None:
        rule = definition["rule"]
        if rule in {1, 3}:
            self._parse_number(raw_data, definition, start, length, signed=False)
        elif rule in {2, 4}:
            self._parse_number(raw_data, definition, start, length, signed=True)
        elif rule == 5:
            self._parse_ascii(raw_data, definition, start, length)
        elif rule in {6, 10}:
            self._parse_register_list(raw_data, definition, start, length, hexadecimal=rule == 6)
        elif rule == 7:
            self._parse_version(raw_data, definition, start, length)
        elif rule == 8:
            self._parse_datetime(raw_data, definition, start, length)
        elif rule == 9:
            self._parse_time(raw_data, definition, start, length)

    @staticmethod
    def _values_for(
        raw_data: list[int], definition: dict[str, Any], start: int, length: int
    ) -> list[int] | None:
        values: list[int] = []
        for register in definition["registers"]:
            index = register - start
            if not 0 <= index < length:
                return None
            values.append(raw_data[index] & 0xFFFF)
        return values

    def _parse_number(
        self,
        raw_data: list[int],
        definition: dict[str, Any],
        start: int,
        length: int,
        *,
        signed: bool,
    ) -> None:
        values = self._values_for(raw_data, definition, start, length)
        if values is None:
            return

        raw_value = sum(value << (index * 16) for index, value in enumerate(values))
        if signed and raw_value & (1 << (len(values) * 16 - 1)):
            raw_value -= 1 << (len(values) * 16)
        if "mask" in definition:
            raw_value &= definition["mask"]

        name = definition["name"]
        if "lookup" in definition:
            self._result[name] = self._lookup(raw_value, definition["lookup"])
            return

        value = (raw_value - definition.get("offset", 0)) * definition.get("scale", 1)
        if division := definition.get("scale_division", 0):
            value //= division
        if not self._is_valid(value, definition.get("validation", {})):
            return
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        self._result[name] = value

    def _parse_ascii(
        self, raw_data: list[int], definition: dict[str, Any], start: int, length: int
    ) -> None:
        values = self._values_for(raw_data, definition, start, length)
        if values is not None:
            self._result[definition["name"]] = "".join(
                chr(value >> 8) + chr(value & 0xFF) for value in values
            ).rstrip("\x00")

    def _parse_register_list(
        self,
        raw_data: list[int],
        definition: dict[str, Any],
        start: int,
        length: int,
        *,
        hexadecimal: bool,
    ) -> None:
        values = self._values_for(raw_data, definition, start, length)
        if values is not None:
            parsed_values = [hex(value) if hexadecimal else value for value in values]
            self._result[definition["name"]] = parsed_values

    def _parse_version(
        self, raw_data: list[int], definition: dict[str, Any], start: int, length: int
    ) -> None:
        values = self._values_for(raw_data, definition, start, length)
        if values is not None:
            self._result[definition["name"]] = ".".join(
                str((value >> shift) & 0x0F) for value in values for shift in (12, 8, 4, 0)
            )

    def _parse_datetime(
        self, raw_data: list[int], definition: dict[str, Any], start: int, length: int
    ) -> None:
        values = self._values_for(raw_data, definition, start, length)
        if values is not None:
            parts = [f"{value >> 8}/{value & 0xFF}" for value in values]
            self._result[definition["name"]] = " ".join(parts)

    def _parse_time(
        self, raw_data: list[int], definition: dict[str, Any], start: int, length: int
    ) -> None:
        values = self._values_for(raw_data, definition, start, length)
        if values is not None:
            value = values[-1]
            self._result[definition["name"]] = f"{value // 100:02d}:{value % 100:02d}"

    @staticmethod
    def _lookup(value: int, options: list[dict[str, Any]]) -> Any:
        return next((option["value"] for option in options if option["key"] == value), value)

    @staticmethod
    def _is_valid(value: float | int, validation: dict[str, Any]) -> bool:
        if "min" in validation and value < validation["min"]:
            if validation.get("invalidate_all"):
                raise ValueError(f"value {value} is below the allowed minimum")
            return False
        if "max" in validation and value > validation["max"]:
            if validation.get("invalidate_all"):
                raise ValueError(f"value {value} is above the allowed maximum")
            return False
        return True
