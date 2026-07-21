#!/usr/bin/env python3
"""Entry point for running from source or freezing with PyInstaller."""

import sys
from simstracker.app import main

if __name__ == "__main__":
    sys.exit(main())
