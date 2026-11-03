#!/usr/bin/env python3
"""Facade pointing to reconcile_tracker_db.py."""

from scripts.reconcile_tracker_db import *  # noqa: F401, F403
from scripts.reconcile_tracker_db import main

if __name__ == "__main__":
    raise SystemExit(main())
