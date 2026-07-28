"""Regression checks for the asynchronous config-flow workers.

These tests deliberately inspect the source because the Home Assistant runtime is
not a development dependency of this repository.  They guard the failure path
which otherwise leaves the flow task with an unbound ``result`` local.
"""

from __future__ import annotations

import ast
from pathlib import Path
import unittest


CONFIG_FLOW = (
    Path(__file__).parents[1]
    / "custom_components"
    / "get_euda_data"
    / "config_flow.py"
)


class ConfigFlowWorkerTests(unittest.TestCase):
    def test_background_workers_initialize_result_before_awaiting_connection(self):
        tree = ast.parse(CONFIG_FLOW.read_text(encoding="utf-8"))
        workers = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name in {"_async_task_login", "_async_task_get_vehicles"}
        }

        self.assertEqual(set(workers), {"_async_task_login", "_async_task_get_vehicles"})
        for worker in workers.values():
            self.assertIsInstance(worker.body[0], ast.Assign)
            self.assertEqual(
                [target.id for target in worker.body[0].targets if isinstance(target, ast.Name)],
                ["result"],
            )
            self.assertIsInstance(worker.body[1], ast.Try)

    def test_reauth_keeps_the_brand_from_the_existing_entry(self):
        source = CONFIG_FLOW.read_text(encoding="utf-8")

        self.assertIn(
            "vol.Required(CONF_BRAND, default=self.entry[CONF_BRAND])",
            source,
        )
        self.assertNotIn(
            "vol.Required(CONF_BRAND, default=brand_values[0])",
            source,
        )


if __name__ == "__main__":
    unittest.main()
