import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FAMILY = ROOT / "production" / "ten-modules"
SPEC = importlib.util.spec_from_file_location("validate_family", FAMILY / "validate_family.py")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class TenModuleFamilyTests(unittest.TestCase):
    def test_production_study_passes_all_gates(self):
        self.assertEqual(validator.main(FAMILY), 0)


if __name__ == "__main__":
    unittest.main()
