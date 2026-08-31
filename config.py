"""Feature-flag configuration loader.\n\nReads flag definitions from a YAML file and returns them as a plain ``dict``\nsuitable for consumption by the flag evaluator.  This module is intentionally\nminimal — it performs **no** schema validation, caching, or evaluation.\n\nPublic API\n----------\nload_config(path)\n    Load a YAML file and return its root mapping as a ``dict``.\n"""

from __future__ import annotations

import logging
import pathlib
from typing import Union

import yaml

__all__ = ["load_config"]

_logger = logging.getLogger(__name__)


def load_config(path: Union[str, pathlib.Path]) -> dict:
    """Load feature-flag definitions from a YAML file.\n\n    Parameters\n    ----------\n    path : str | pathlib.Path\n        Filesystem path to a YAML file containing flag definitions.\n        Both ``str`` and :class:`pathlib.Path` values are accepted.\n\n    Returns\n    -------\n    dict\n        The root mapping parsed from the YAML file.  If the file is empty,\n        contains a non-mapping root value (e.g. a list or scalar), or cannot\n        be read due to a recoverable I/O or YAML-syntax error, an empty\n        ``dict`` (``{}``) is returned instead.\n\n    Notes\n    -----\n    The following error classes are handled gracefully — a ``WARNING`` is\n    logged and ``{}`` is returned:\n\n    * ``FileNotFoundError``\n    * ``PermissionError``\n    * ``OSError`` (any other I/O error)\n    * ``yaml.YAMLError`` (malformed YAML)\n\n    Unrelated exceptions (e.g. ``TypeError`` from a wrong-typed *path*)\n    are **not** caught and will propagate normally.\n\n    Only :func:`yaml.safe_load` is used for parsing so that untrusted input\n    cannot deserialize arbitrary Python objects.\n    """
    try:
        with open(path, mode="r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except FileNotFoundError:
        _logger.warning("Configuration file not found: %s", path)
        return {}
    except PermissionError:
        _logger.warning("Permission denied when reading configuration file: %s", path)
        return {}
    except OSError as exc:
        _logger.warning(
            "I/O error reading configuration file %s: %s", path, exc,
        )
        return {}
    except yaml.YAMLError as exc:
        _logger.warning(
            "Failed to parse YAML from %s: %s", path, exc,
        )
        return {}

    if not isinstance(data, dict):
        # Covers None (empty file) and non-mapping roots (list, scalar).
        return {}

    return data