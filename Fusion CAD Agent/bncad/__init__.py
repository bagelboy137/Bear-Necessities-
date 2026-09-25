"""bncad - build 3D CAD models from part specs using a local model.

    from bncad import PartSpec, build, resolve

CadQuery builds the geometry headlessly so the loop runs unattended; Fusion
picks the result up when it is open. See README.md in this folder.
"""
__version__ = "1.0.0"

from .spec import PartSpec, SpecError, measure, load_all      # noqa: F401
from .provider import Provider, ProviderError, resolve, discover  # noqa: F401
from .loop import build, guard, extract_code                  # noqa: F401
