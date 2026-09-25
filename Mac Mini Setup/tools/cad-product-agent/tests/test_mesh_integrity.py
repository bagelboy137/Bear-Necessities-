import importlib.util
import pathlib
import struct
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FAMILY = ROOT / "production" / "ten-modules"
SPEC = importlib.util.spec_from_file_location("mesh_integrity", FAMILY / "mesh_integrity.py")
mesh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mesh)


def _write_stl(path, triangles):
    body = b"".join(
        struct.pack("<12f", *t[0], *t[1], *t[2], *t[3]) + b"\x00\x00"
        for t in triangles)
    path.write_bytes(b"unit test".ljust(80, b" ")
                     + struct.pack("<I", len(triangles)) + body)


def check(path, job):
    return mesh.check_file(path, job, tolerance_in=0.01, scale=mesh.MM_PER_INCH)


class MeshIntegrityTests(unittest.TestCase):
    def test_topology_selftest(self):
        self.assertEqual(mesh.selftest(), 0)

    def test_shipped_exports_pass(self):
        report = mesh.evaluate(FAMILY / "jobs", FAMILY / "exports", 0.01, "mm")
        self.assertEqual(report["modules_checked"], 10)
        self.assertTrue(report["pass"], report["failures"])

    def test_touching_bodies_are_not_reported_broken(self):
        """The regression that made the first version of this gate cry wolf."""
        soup = mesh._cube() + mesh._cube(origin=(1.0, 1.0, 0.0))
        self.assertFalse(mesh.inspect(soup)["watertight"])
        solids = mesh.split_solids(soup)
        self.assertEqual(len(solids), 2)
        for solid in solids:
            self.assertTrue(mesh.inspect(solid)["watertight"])

    def test_scale_error_and_dropped_body_are_caught(self):
        job = {
            "module_id": "TEST",
            "frame": {"outside_in": [10.0, 10.0, 10.0],
                      "cut_list": [{"length": 10.0, "quantity": 1}]},
            "components": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            # a single 254mm cube == the declared 10in envelope: clean
            good = pathlib.Path(tmp) / "good.stl"
            _write_stl(good, mesh._cube(size=254.0))
            self.assertTrue(check(good, job)["pass"])

            # same cube exported in inches instead of mm
            bad_scale = pathlib.Path(tmp) / "scale.stl"
            _write_stl(bad_scale, mesh._cube(size=10.0))
            reasons = check(bad_scale, job)["reasons"]
            self.assertTrue(any("export units/scale" in r for r in reasons), reasons)

            # an extra body the job never declared
            extra = pathlib.Path(tmp) / "extra.stl"
            _write_stl(extra, mesh._cube(size=254.0)
                       + mesh._cube(origin=(300.0, 0.0, 0.0), size=5.0))
            reasons = check(extra, job)["reasons"]
            self.assertTrue(any("solids in STL" in r for r in reasons), reasons)

            # a body with a hole punched in it
            holed = pathlib.Path(tmp) / "holed.stl"
            _write_stl(holed, mesh._cube(size=254.0)[:-1])
            reasons = check(holed, job)["reasons"]
            self.assertTrue(any("boundary" in r for r in reasons), reasons)


if __name__ == "__main__":
    unittest.main()
