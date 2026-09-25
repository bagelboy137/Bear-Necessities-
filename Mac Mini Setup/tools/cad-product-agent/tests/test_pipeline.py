import importlib.util
import json
import pathlib
import tempfile
import types
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("professional_pipeline", ROOT / "professional_pipeline.py")
pipeline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pipeline)


class JobValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fusion_root = pathlib.Path(__file__).resolve().parents[4] / "Fusion CAD Agent"
        cls.template = json.loads((ROOT / "templates" / "bear-base-frame.job.json").read_text())

    def test_prototype_template_is_valid(self):
        self.assertEqual(pipeline.validate_job(self.template, self.fusion_root), [])

    def test_release_candidate_requires_load_and_safety_factor(self):
        job = json.loads(json.dumps(self.template))
        job["status"] = "READY_RELEASE_CANDIDATE"
        errors = pipeline.validate_job(job, self.fusion_root)
        self.assertTrue(any("load_case" in error for error in errors))
        self.assertTrue(any("safety_factor_target" in error for error in errors))
        self.assertTrue(any("native assembly" in error for error in errors))
        self.assertTrue(any("component_count" in error for error in errors))

    def test_interface_requires_provenance(self):
        job = json.loads(json.dumps(self.template))
        del job["engineering"]["interfaces"][0]["source_ref"]
        errors = pipeline.validate_job(job, self.fusion_root)
        self.assertTrue(any("source_ref" in error for error in errors))

    def test_path_escape_is_rejected(self):
        job = json.loads(json.dumps(self.template))
        job["spec_path"] = "../../etc/passwd"
        errors = pipeline.validate_job(job, self.fusion_root)
        self.assertTrue(any("escapes Fusion project" in error for error in errors))


class ReleaseTests(unittest.TestCase):
    def test_release_check_never_accepts_auto_released_report(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = pathlib.Path(temp)
            report = {
                "automated_gates_passed": True,
                "artifacts": [{"name": "part.step"}],
                "scripts": [{"name": "part.py"}],
                "missing_deliverables": [],
                "human_review_required": True,
                "release_status": "RELEASED",
            }
            (run_dir / "report.json").write_text(json.dumps(report))
            self.assertEqual(pipeline.release_check(run_dir), 1)

    def test_complete_candidate_stops_at_human_review(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = pathlib.Path(temp)
            report = {
                "automated_gates_passed": True,
                "artifacts": [{"name": "part.step"}],
                "scripts": [{"name": "part.py"}],
                "missing_deliverables": [],
                "human_review_required": True,
                "release_status": "AWAITING_HUMAN_REVIEW",
            }
            (run_dir / "report.json").write_text(json.dumps(report))
            self.assertEqual(pipeline.release_check(run_dir), 0)


if __name__ == "__main__":
    unittest.main()
