"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

# Ensure src is on path when running tests
src = Path(__file__).resolve().parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))
