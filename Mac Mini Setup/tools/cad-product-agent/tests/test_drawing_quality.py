import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

import ezdxf


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("drawing_quality", ROOT / "drawing_quality.py")
quality = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(quality)


def make_dxf(path, complete=True):
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 1
    for layer in quality.REQUIRED_LAYERS:
        if layer not in doc.layers:
            doc.layers.add(layer)
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (24, 0), (24, 18), (0, 18)], close=True,
                       dxfattribs={"layer": "OUTLINE"})
    msp.add_line((0, 9), (24, 9), dxfattribs={"layer": "CENTER"})
    msp.add_line((0, 0), (24, 18), dxfattribs={"layer": "HIDDEN"})
    msp.add_lwpolyline([(0, -4), (24, -4), (24, -1), (0, -1)], close=True,
                       dxfattribs={"layer": "TITLEBLOCK"})
    phrases = ["BN-MCS-BASE-001", "REV P1", "6063-T6 ALUMINUM EXTRUSION",
               "CUT-TO-LENGTH", "UNITS: INCH", "DO NOT SCALE", "TOLERANCE",
               "PROTOTYPE - NOT FOR FABRICATION"]
    for index, phrase in enumerate(phrases):
        msp.add_text(phrase, height=0.2, dxfattribs={"layer": "TITLEBLOCK"}).set_placement((index * 0.1, -2))
    if complete:
        for offset in range(4):
            dim = msp.add_linear_dim(base=(0, 20 + offset), p1=(0, 0), p2=(24, 0),
                                     angle=0, dxfattribs={"layer": "DIMENSIONS"})
            dim.render()
        msp.add_text("FRONT TOP RIGHT", height=0.25,
                     dxfattribs={"layer": "TEXT"}).set_placement((0, 22))
    doc.saveas(path)


class DrawingQualityTests(unittest.TestCase):
    def setUp(self):
        self.job = ROOT / "templates" / "bear-base-frame.job.json"

    def test_compliant_fixture_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            drawing = pathlib.Path(temp) / "ok.dxf"
            make_dxf(drawing, complete=True)
            with mock.patch.object(sys, "argv", ["drawing_quality.py", str(self.job), str(drawing)]):
                self.assertEqual(quality.main(), 0)

    def test_missing_dimensions_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            drawing = pathlib.Path(temp) / "bad.dxf"
            make_dxf(drawing, complete=False)
            with mock.patch.object(sys, "argv", ["drawing_quality.py", str(self.job), str(drawing)]):
                self.assertEqual(quality.main(), 1)


if __name__ == "__main__":
    unittest.main()
