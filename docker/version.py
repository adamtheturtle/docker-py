try:
    from ._version import __version__
except ImportError:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version('docker')
    except PackageNotFoundError:
        __version__ = '0.0.0'

__all__ = ['__version__']
