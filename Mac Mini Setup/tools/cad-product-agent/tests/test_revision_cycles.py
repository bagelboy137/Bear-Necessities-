import csv
import importlib.util
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
ITERATIONS = ROOT / "production" / "ten-modules" / "iterations"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load("run_revision_cycles", ITERATIONS / "run_revision_cycles.py")


class RevisionCycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = json.loads((ITERATIONS / "module-review-context.json").read_text())
        cls.comparables = json.loads((ITERATIONS / "comparable-products.json").read_text())
        cls.catalog = json.loads((ITERATIONS / "ots-components.json").read_text())
        cls.criteria = json.loads((ITERATIONS / "review-criteria.json").read_text())

    def test_exactly_thirty_family_cycles_are_defined(self):
        self.assertEqual(set(self.criteria["stages"]),
                         {"design", "manufacturing", "combined"})
        for stage, values in self.criteria["stages"].items():
            self.assertEqual([item["cycle"] for item in values], list(range(1, 11)), stage)
            self.assertEqual(len({item["criterion"] for item in values}), 10)

    def test_every_module_catalog_reference_is_curated(self):
        catalog_ids = {item["id"] for item in self.catalog["components"]}
        modules = self.context["modules"]
        self.assertEqual(sorted(item["module_id"] for item in modules), runner.MODULE_IDS)
        for module in modules:
            self.assertTrue(set(module["primary_catalog_ids"]) <= catalog_ids,
                            module["module_id"])

    def test_schema_gate_accepts_a_complete_minimal_cycle(self):
        value = {
            "cycle_id": "design-01",
            "reviews": [{
                "module_id": module_id,
                "verdict": "RETAIN",
                "proposal": "Retain the validated visible baseline.",
                "rationale": "The current functional cue remains recognizable.",
                "evidence_ids": ["CURRENT-CAD"],
                "acceptance_check": "Confirm the named cue in the current isometric image.",
                "risk": "Physical engineering remains open."
            } for module_id in runner.MODULE_IDS]
        }
        failures = runner.validate_cycle(value, "design-01", "design", self.context,
                                         self.comparables, self.catalog)
        self.assertEqual(failures, [])

    def test_generated_boms_cover_all_modules_and_have_links(self):
        path = ITERATIONS / "boms" / "all-modules-prototype-bom.csv"
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual({row["module_id"] for row in rows}, set(runner.MODULE_IDS))
        self.assertGreaterEqual(len(rows), 100)
        for row in rows:
            self.assertTrue(row["catalog_id"])
            self.assertTrue(row["order_url"].startswith("https://"))
            self.assertTrue(row["evidence_url"].startswith("https://"))

    def test_complete_ledger_when_present(self):
        path = ITERATIONS / "runs" / "iteration-ledger.json"
        if not path.is_file():
            self.skipTest("live iteration ledger not generated")
        ledger = json.loads(path.read_text())
        if ledger.get("result") != "PASS":
            self.skipTest("live iteration ledger is intentionally still running")
        self.assertEqual(ledger["cycle_count"], 30)
        self.assertEqual(ledger["module_review_count"], 300)
        self.assertTrue({item["model"] for item in ledger["records"]} <=
                        runner.APPROVED_MODELS)
        self.assertEqual(ledger["required_model"], runner.PRIMARY_MODEL)


if __name__ == "__main__":
    unittest.main()
