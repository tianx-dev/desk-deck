"""Desk Deck: a local Nest Hub interface and task feed."""

import sys

if sys.version_info < (3, 11):
    raise SystemExit(
        "Desk Deck requires Python 3.11 or newer. Select that interpreter before creating the virtual environment."
    )

__version__ = "0.1.0"
