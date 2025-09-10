#!/usr/bin/env python3
"""Default report generation script - uses minimalist HTML reports."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import and run the main report script
from report_main import main

if __name__ == "__main__":
    sys.exit(main())