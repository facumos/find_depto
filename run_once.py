#!/usr/bin/env python3
"""Run the apartment bot once (for cron usage)."""

import os
import sys

# Change to script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import check_and_notify
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    check_and_notify()
