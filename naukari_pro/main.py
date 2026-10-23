"""
naukariPro Main CLI Entry Point
Forwards CLI execution directly to naukari_pro.cli:main
"""
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from naukari_pro.cli import main

if __name__ == "__main__":
    main()
