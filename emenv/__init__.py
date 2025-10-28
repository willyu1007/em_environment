"""Top-level package for the EM environment estimation service."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("emenv")
except PackageNotFoundError:  # pragma: no cover - fallback when package isn't installed
    __version__ = "0.1.0"

from .engine import ComputeEngine, ComputeResult

__all__ = ["ComputeEngine", "ComputeResult", "__version__"]
