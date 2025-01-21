"""
:mod:`tugboat`, the main package of the Tugboat framework.

The Tugboat framework is a modular static analysis tool for software manifests.
It is designed to examine software manifests and report issues detected by the
analyzers.

This package exposes only the core components of the framework:

- :class:`Diagnosis`: The primary structure for a diagnosis.
- :data:`hookimpl`: The hook implementation marker for the Tugboat framework.

Other components are available in the subpackages of the framework but are not
automatically imported here; they are intended to be imported explicitly by
the user.
"""

__all__ = [
    "Diagnosis",
    "__version__",
    "hookimpl",
]

from tugboat.core import hookimpl
from tugboat.types import Diagnosis
from tugboat.version import __version__
