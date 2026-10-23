#!/usr/bin/env python3
"""
CLI entrypoint wrapper for naukariPro suite.
Allows execution via `.venv/bin/python cli.py <command>`.
"""
import sys
from naukari_pro.cli import main

if __name__ == "__main__":
    main()
