"""OKFX: concept inheritance, content integrity and declarative validation for OKF v0.2.

An independent extension to Google Cloud's Open Knowledge Format. Every OKFX
document remains a valid OKF v0.2 document; every family here is optional.
"""

from importlib.metadata import PackageNotFoundError, version

from .document import Document, DocumentError, OKFXError
from .integrity import IntegrityError, compute, seal, verify
from .resolve import ResolveError, resolve
from .validation import ValidationError, ValidatorsRefused

__all__ = [
    "Document",
    "DocumentError",
    "IntegrityError",
    "OKFXError",
    "ResolveError",
    "ValidationError",
    "ValidatorsRefused",
    "compute",
    "resolve",
    "seal",
    "verify",
]
try:
    # Read from the installed distribution rather than restating it here: the
    # hand-written copy had already drifted three releases behind pyproject.toml.
    __version__ = version("okfx")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0+unknown"
