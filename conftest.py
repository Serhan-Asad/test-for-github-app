"""Project-level pytest configuration.

The harness uses .tsx as the file extension for test files in this PDD
project even though the test bodies are written in Python. Teach pytest
to collect them by loading the file via importlib.
"""

import importlib.util
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest


class TsxModule(pytest.Module):
    def _getobj(self):
        path = Path(self.path)
        name = path.stem
        loader = SourceFileLoader(name, str(path))
        spec = importlib.util.spec_from_loader(name, loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        loader.exec_module(module)
        return module


def pytest_collect_file(parent, file_path):
    p = Path(file_path)
    if p.suffix == ".tsx" and p.name.startswith("test_"):
        return TsxModule.from_parent(parent, path=p)
    return None
