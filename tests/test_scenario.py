import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IncidentScenarioTests(unittest.TestCase):
    def test_healthy_incident_and_recovery(self):
        nginx = os.environ.get("NGINX_BIN") or shutil.which("nginx")
        if not nginx:
            self.skipTest("Nginx is required for the live integration test")
        result = subprocess.run(
            [sys.executable, str(ROOT / "run_scenario.py"), "--nginx", nginx],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual([report[name]["proxy_status"] for name in ("healthy", "incident", "recovered")], [200, 502, 200])
        self.assertTrue(all(report[name]["upstream_health"] == 200 for name in report))
        self.assertTrue(report["incident"]["connection_refused_in_proxy_log"])
        self.assertEqual(report["healthy"]["response"], "incident-lab-ok")
        self.assertEqual(report["recovered"]["response"], "incident-lab-ok")


if __name__ == "__main__":
    unittest.main()
