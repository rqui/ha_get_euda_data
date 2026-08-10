"""Regression tests for merging partial EUDA data files.

The EU Data Act portal delivers *partial* files: each downloaded file only
contains a subset of the vehicle's data fields. Before this fix,
``EUDAConnection.extractInformationFromFile`` replaced ``currentData``
wholesale with the contents of the newest file, so any field missing from
that particular file (e.g. state of charge, charging state) would appear as
"unknown" in Home Assistant even though a previous file had reported a valid
value minutes earlier.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


PACKAGE_DIR = (
    Path(__file__).parents[1] / "custom_components" / "get_euda_data" / "get_euda_data"
)


def _load_package():
    """Load the get_euda_data package so relative imports in eudaconnection.py work."""
    package_name = "get_euda_data_under_test"
    if package_name in sys.modules:
        return sys.modules[package_name + ".eudaconnection"]

    package = ModuleType(package_name)
    package.__path__ = [str(PACKAGE_DIR)]
    sys.modules[package_name] = package

    spec = importlib.util.spec_from_file_location(
        package_name + ".eudaconnection", PACKAGE_DIR / "eudaconnection.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[package_name + ".eudaconnection"] = module
    spec.loader.exec_module(module)
    return module


def _write_data_file(directory: Path, vin: str, timestamp: str, fields: dict) -> Path:
    """Write a minimal EUDA-style JSON file with the given key/value fields."""
    data = {
        "vin": vin,
        "user_id": "test-user",
        "Data": [
            {
                "key": key,
                "dataFieldName": key,
                "value": value,
                "timestampUtc": timestamp,
            }
            for key, value in fields.items()
        ],
    }
    path = directory / f"{vin}_{timestamp}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class MergePartialEudaFilesTests(unittest.TestCase):
    def test_field_missing_from_newest_file_keeps_its_last_known_value(self):
        eudaconnection = _load_package()

        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                conn = eudaconnection.EUDAConnection(session=None)
                vin = "VSSZZZKS0VR003238"

                # First file: reports state_of_charge and mileage.
                older = _write_data_file(
                    Path(tmpdir),
                    vin,
                    "20260807081336",
                    {
                        "battery_state_report.soc": "70",
                        "mileage.value": "1413",
                    },
                )
                # Second, newer file: only reports mileage (soc is absent, as
                # happens with real partial EUDA files).
                newer = _write_data_file(
                    Path(tmpdir),
                    vin,
                    "20260810065604",
                    {
                        "mileage.value": "1458",
                    },
                )

                async def run():
                    for path in (older, newer):
                        with os.scandir(path.parent) as entries:
                            entry = next(
                                e for e in entries if e.name == path.name
                            )
                            self.assertTrue(
                                await conn.extractInformationFromFile(entry)
                            )

                asyncio.run(run())

                fields = {
                    element["key"]: element["value"]
                    for element in conn.currentData[vin]["Data"]
                }

                # The newer file's own field must win.
                self.assertEqual(fields["mileage.value"], "1458")
                # The field absent from the newer file must NOT disappear -
                # it should still carry the last known value instead of the
                # sensor going "unknown" in Home Assistant.
                self.assertEqual(fields["battery_state_report.soc"], "70")
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
