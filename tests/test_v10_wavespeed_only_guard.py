import unittest
from pathlib import Path


FORBIDDEN_IMPORTS = [
    "openai",
    "anthropic",
    "google.generativeai",
    "replicate",
    "fal_client",
    "runwayml",
]


class V10WaveSpeedOnlyGuardTests(unittest.TestCase):
    def test_app_code_does_not_import_non_wavespeed_ai_clients(self):
        root = Path(__file__).resolve().parents[1] / "app"
        offenders = []
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for forbidden in FORBIDDEN_IMPORTS:
                if f"import {forbidden}" in text or f"from {forbidden}" in text:
                    offenders.append(f"{path.relative_to(root)}:{forbidden}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
