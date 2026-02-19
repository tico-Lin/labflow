"""
Integration adapters and registry.
"""

from .registry import get_adapter, list_specs, register_adapter
from .adapters.impedance_adapter import ImpedanceAdapter


register_adapter(ImpedanceAdapter())

try:
	from .adapters.pyfai_adapter import PyFAIAdapter
except ImportError:
	PyFAIAdapter = None
else:
	register_adapter(PyFAIAdapter())

try:
	from .adapters.skimage_adapter import SkimageAdapter
except ImportError:
	SkimageAdapter = None
else:
	register_adapter(SkimageAdapter())

try:
	from .adapters.pymatgen_adapter import PymatgenAdapter
except ImportError:
	PymatgenAdapter = None
else:
	register_adapter(PymatgenAdapter())

try:
	from .adapters.mendeleev_adapter import MendeleevAdapter
except ImportError:
	MendeleevAdapter = None
else:
	register_adapter(MendeleevAdapter())

try:
	from .adapters.h5py_adapter import Hdf5StorageAdapter
except ImportError:
	Hdf5StorageAdapter = None
else:
	register_adapter(Hdf5StorageAdapter())

try:
	from .adapters.docx_report_adapter import DocxReportAdapter
except ImportError:
	DocxReportAdapter = None
else:
	register_adapter(DocxReportAdapter())

try:
	from .adapters.xrd_match_adapter import XrdMatchAdapter
except ImportError:
	XrdMatchAdapter = None
else:
	register_adapter(XrdMatchAdapter())

try:
	from .adapters.matminer_adapter import MatminerAdapter
except ImportError:
	MatminerAdapter = None
else:
	register_adapter(MatminerAdapter())

__all__ = ["get_adapter", "list_specs", "register_adapter"]
