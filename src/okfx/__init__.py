"""OKFX: concept inheritance, content integrity and declarative validation for OKF v0.2.

An independent extension to Google Cloud's Open Knowledge Format. Every OKFX
document remains a valid OKF v0.2 document; every family here is optional.
"""

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
__version__ = "0.1.0"
