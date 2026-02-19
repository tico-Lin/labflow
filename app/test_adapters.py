"""
Adapter tests with mocked dependencies to raise coverage for integrations.
"""

import sys
import types
import importlib
import numpy as np

import pytest

from app.integrations.base import ToolContext
from app.integrations.registry import register_adapter, get_adapter, list_specs


def make_fake_skimage(monkeypatch):
    skimage = types.ModuleType("skimage")
    skimage_io = types.ModuleType("skimage.io")
    skimage_feature = types.ModuleType("skimage.feature")
    skimage_filters = types.ModuleType("skimage.filters")

    def imread(path, as_gray=False):
        return np.ones((3, 3), dtype=float)

    def canny(image, sigma=1.0):
        return np.zeros_like(image, dtype=bool)

    def gaussian(image, sigma=1.0):
        return image * 0.5

    skimage_io.imread = imread
    skimage_feature.canny = canny
    skimage_filters.gaussian = gaussian

    monkeypatch.setitem(sys.modules, "skimage", skimage)
    monkeypatch.setitem(sys.modules, "skimage.io", skimage_io)
    monkeypatch.setitem(sys.modules, "skimage.feature", skimage_feature)
    monkeypatch.setitem(sys.modules, "skimage.filters", skimage_filters)


@pytest.mark.unit
def test_skimage_adapter_canny(monkeypatch):
    make_fake_skimage(monkeypatch)
    skimage_adapter = importlib.import_module("app.integrations.adapters.skimage_adapter")
    adapter = skimage_adapter.SkimageAdapter()
    context = ToolContext(
        filename="img.png",
        file_bytes=b"fake",
        file_path="dummy",
        parameters={"operation": "canny", "sigma": 1.5},
    )
    result = adapter.run(context)
    assert result.status == "completed"
    assert "metrics" in result.output


@pytest.mark.unit
def test_skimage_adapter_missing_bytes():
    skimage_adapter = importlib.import_module("app.integrations.adapters.skimage_adapter")
    adapter = skimage_adapter.SkimageAdapter()
    result = adapter.run(ToolContext(filename="img.png", file_bytes=None, parameters={"operation": "canny"}))
    assert result.status == "failed"


@pytest.mark.unit
def test_skimage_adapter_missing_operation(monkeypatch):
    make_fake_skimage(monkeypatch)
    skimage_adapter = importlib.import_module("app.integrations.adapters.skimage_adapter")
    adapter = skimage_adapter.SkimageAdapter()
    result = adapter.run(ToolContext(filename="img.png", file_bytes=b"fake", file_path="dummy", parameters={}))
    assert result.status == "failed"


@pytest.mark.unit
def test_skimage_adapter_unknown_operation(monkeypatch):
    make_fake_skimage(monkeypatch)
    skimage_adapter = importlib.import_module("app.integrations.adapters.skimage_adapter")
    adapter = skimage_adapter.SkimageAdapter()
    context = ToolContext(
        filename="img.png",
        file_bytes=b"fake",
        file_path="dummy",
        parameters={"operation": "unknown"},
    )
    result = adapter.run(context)
    assert result.status == "failed"


@pytest.mark.unit
def test_skimage_adapter_imread_error(monkeypatch):
    make_fake_skimage(monkeypatch)
    skimage_adapter = importlib.import_module("app.integrations.adapters.skimage_adapter")
    skimage_io = sys.modules["skimage.io"]
    monkeypatch.setattr(skimage_io, "imread", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("bad")))
    adapter = skimage_adapter.SkimageAdapter()
    context = ToolContext(
        filename="img.png",
        file_bytes=b"fake",
        file_path="dummy",
        parameters={"operation": "canny"},
    )
    result = adapter.run(context)
    assert result.status == "failed"


@pytest.mark.unit
def test_pyfai_adapter_success(monkeypatch):
    make_fake_skimage(monkeypatch)

    pyfai = types.ModuleType("pyFAI")

    class FakeIntegrator:
        def integrate1d(self, image, npt, unit=None):
            radial = np.arange(npt, dtype=float)
            intensity = np.arange(npt, dtype=float) * 2
            return radial, intensity

    def load(path):
        return FakeIntegrator()

    pyfai.load = load
    monkeypatch.setitem(sys.modules, "pyFAI", pyfai)

    pyfai_adapter = importlib.import_module("app.integrations.adapters.pyfai_adapter")
    adapter = pyfai_adapter.PyFAIAdapter()
    context = ToolContext(
        filename="img.tiff",
        file_bytes=b"fake",
        file_path="dummy",
        parameters={"poni_file": "calib.poni", "npt": 3, "unit": "2th_deg"},
    )
    result = adapter.run(context)
    assert result.status == "completed"
    assert result.output["npt"] == 3


@pytest.mark.unit
def test_pyfai_adapter_missing_bytes(monkeypatch):
    make_fake_skimage(monkeypatch)
    pyfai_adapter = importlib.import_module("app.integrations.adapters.pyfai_adapter")
    adapter = pyfai_adapter.PyFAIAdapter()
    result = adapter.run(ToolContext(filename="img.tiff", file_bytes=None, parameters={"poni_file": "x"}))
    assert result.status == "failed"


@pytest.mark.unit
def test_pyfai_adapter_missing_poni_file(monkeypatch):
    make_fake_skimage(monkeypatch)
    pyfai = types.ModuleType("pyFAI")
    pyfai.load = lambda path: None
    monkeypatch.setitem(sys.modules, "pyFAI", pyfai)

    pyfai_adapter = importlib.import_module("app.integrations.adapters.pyfai_adapter")
    adapter = pyfai_adapter.PyFAIAdapter()
    result = adapter.run(ToolContext(filename="img.tiff", file_bytes=b"fake", file_path="dummy", parameters={}))
    assert result.status == "failed"


@pytest.mark.unit
def test_pyfai_adapter_import_error(monkeypatch):
    make_fake_skimage(monkeypatch)
    monkeypatch.delitem(sys.modules, "pyFAI", raising=False)
    pyfai_adapter = importlib.import_module("app.integrations.adapters.pyfai_adapter")
    adapter = pyfai_adapter.PyFAIAdapter()
    result = adapter.run(ToolContext(filename="img.tiff", file_bytes=b"fake", file_path="dummy", parameters={"poni_file": "x"}))
    assert result.status == "failed"


@pytest.mark.unit
def test_pyfai_adapter_integration_error(monkeypatch):
    make_fake_skimage(monkeypatch)
    pyfai = types.ModuleType("pyFAI")
    pyfai.load = lambda path: (_ for _ in ()).throw(RuntimeError("bad"))
    monkeypatch.setitem(sys.modules, "pyFAI", pyfai)

    pyfai_adapter = importlib.import_module("app.integrations.adapters.pyfai_adapter")
    adapter = pyfai_adapter.PyFAIAdapter()
    context = ToolContext(
        filename="img.tiff",
        file_bytes=b"fake",
        file_path="dummy",
        parameters={"poni_file": "x"},
    )
    result = adapter.run(context)
    assert result.status == "failed"


@pytest.mark.unit
def test_impedance_adapter_success(monkeypatch):
    impedance = types.ModuleType("impedance")
    models = types.ModuleType("impedance.models")
    circuits = types.ModuleType("impedance.models.circuits")

    class FakeRandles:
        def __init__(self, initial_guess=None):
            self.parameters_ = np.array([1.0, 2.0, 3.0, 4.0], dtype=float)
            self.chi_squared_ = 0.5

        def fit(self, freq, z):
            return None

        def get_param_names(self):
            return ["R0", "R1", "C1", "W"]

    circuits.Randles = FakeRandles
    models.circuits = circuits
    impedance.models = models

    monkeypatch.setitem(sys.modules, "impedance", impedance)
    monkeypatch.setitem(sys.modules, "impedance.models", models)
    monkeypatch.setitem(sys.modules, "impedance.models.circuits", circuits)

    impedance_adapter = importlib.import_module("app.integrations.adapters.impedance_adapter")
    adapter = impedance_adapter.ImpedanceAdapter()
    csv_data = b"frequency,zreal,zimag\n1,1,0\n2,2,0"
    context = ToolContext(filename="eis.csv", file_bytes=csv_data, parameters={})
    result = adapter.run(context)
    assert result.status == "completed"
    assert result.output["data_points"] == 2


@pytest.mark.unit
def test_impedance_adapter_missing_bytes():
    impedance_adapter = importlib.import_module("app.integrations.adapters.impedance_adapter")
    adapter = impedance_adapter.ImpedanceAdapter()
    result = adapter.run(ToolContext(filename="eis.csv", file_bytes=None, parameters={}))
    assert result.status == "failed"


@pytest.mark.unit
def test_impedance_adapter_import_error(monkeypatch):
    impedance_adapter = importlib.import_module("app.integrations.adapters.impedance_adapter")
    real_import = importlib.import_module

    def fake_import(name, package=None):
        if name == "impedance.models.circuits":
            raise ImportError("impedance not available")
        return real_import(name, package)

    monkeypatch.setattr(impedance_adapter.importlib, "import_module", fake_import)
    adapter = impedance_adapter.ImpedanceAdapter()
    csv_data = b"frequency,zreal,zimag\n1,1,0"
    result = adapter.run(ToolContext(filename="eis.csv", file_bytes=csv_data, parameters={}))
    assert result.status == "failed"


@pytest.mark.unit
def test_impedance_adapter_missing_columns(monkeypatch):
    impedance = types.ModuleType("impedance")
    models = types.ModuleType("impedance.models")
    circuits = types.ModuleType("impedance.models.circuits")

    class FakeRandles:
        def __init__(self, initial_guess=None):
            self.parameters_ = np.array([1.0, 2.0, 3.0, 4.0], dtype=float)
            self.chi_squared_ = 0.5

        def fit(self, freq, z):
            return None

        def get_param_names(self):
            return ["R0", "R1", "C1", "W"]

    circuits.Randles = FakeRandles
    models.circuits = circuits
    impedance.models = models

    monkeypatch.setitem(sys.modules, "impedance", impedance)
    monkeypatch.setitem(sys.modules, "impedance.models", models)
    monkeypatch.setitem(sys.modules, "impedance.models.circuits", circuits)

    impedance_adapter = importlib.import_module("app.integrations.adapters.impedance_adapter")
    adapter = impedance_adapter.ImpedanceAdapter()
    csv_data = b"freq,zreal\n1,1"
    result = adapter.run(ToolContext(filename="eis.csv", file_bytes=csv_data, parameters={}))
    assert result.status == "failed"


@pytest.mark.unit
def test_impedance_adapter_parse_error(monkeypatch):
    impedance = types.ModuleType("impedance")
    models = types.ModuleType("impedance.models")
    circuits = types.ModuleType("impedance.models.circuits")

    class FakeRandles:
        def __init__(self, initial_guess=None):
            self.parameters_ = np.array([1.0, 2.0, 3.0, 4.0], dtype=float)
            self.chi_squared_ = 0.5

        def fit(self, freq, z):
            return None

        def get_param_names(self):
            return ["R0", "R1", "C1", "W"]

    circuits.Randles = FakeRandles
    models.circuits = circuits
    impedance.models = models

    monkeypatch.setitem(sys.modules, "impedance", impedance)
    monkeypatch.setitem(sys.modules, "impedance.models", models)
    monkeypatch.setitem(sys.modules, "impedance.models.circuits", circuits)

    impedance_adapter = importlib.import_module("app.integrations.adapters.impedance_adapter")
    monkeypatch.setattr(impedance_adapter.pd, "read_csv", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("bad")))
    adapter = impedance_adapter.ImpedanceAdapter()
    result = adapter.run(ToolContext(filename="eis.csv", file_bytes=b"not csv", parameters={}))
    assert result.status == "failed"


@pytest.mark.unit
def test_registry_register_and_get(monkeypatch):
    make_fake_skimage(monkeypatch)
    skimage_adapter = importlib.import_module("app.integrations.adapters.skimage_adapter")
    adapter = skimage_adapter.SkimageAdapter()
    register_adapter(adapter)
    fetched = get_adapter(adapter.spec.id)
    assert fetched.spec.id == adapter.spec.id
    specs = list_specs()
    assert any(spec.id == adapter.spec.id for spec in specs)


@pytest.mark.unit
def test_pymatgen_adapter_missing_bytes():
    pymatgen_adapter = importlib.import_module("app.integrations.adapters.pymatgen_adapter")
    adapter = pymatgen_adapter.PymatgenAdapter()
    result = adapter.run(ToolContext(filename="sample.cif", file_bytes=None, parameters={}))
    assert result.status == "failed"


@pytest.mark.unit
def test_mendeleev_adapter_missing_element():
    mendeleev_adapter = importlib.import_module("app.integrations.adapters.mendeleev_adapter")
    adapter = mendeleev_adapter.MendeleevAdapter()
    result = adapter.run(ToolContext(filename="sample.txt", file_bytes=b"fake", parameters={}))
    assert result.status == "failed"


@pytest.mark.unit
def test_hdf5_adapter_missing_bytes():
    h5py_adapter = importlib.import_module("app.integrations.adapters.h5py_adapter")
    adapter = h5py_adapter.Hdf5StorageAdapter()
    result = adapter.run(ToolContext(filename="data.csv", file_bytes=None, parameters={}))
    assert result.status == "failed"


@pytest.mark.unit
def test_xrd_match_adapter_missing_reference():
    xrd_adapter = importlib.import_module("app.integrations.adapters.xrd_match_adapter")
    adapter = xrd_adapter.XrdMatchAdapter()
    result = adapter.run(ToolContext(filename="xrd.csv", file_bytes=b"2theta,intensity\n1,1", parameters={}))
    assert result.status == "failed"


@pytest.mark.unit
def test_matminer_adapter_missing_composition():
    matminer_adapter = importlib.import_module("app.integrations.adapters.matminer_adapter")
    adapter = matminer_adapter.MatminerAdapter()
    result = adapter.run(ToolContext(filename="sample.txt", file_bytes=b"fake", parameters={}))
    assert result.status == "failed"
