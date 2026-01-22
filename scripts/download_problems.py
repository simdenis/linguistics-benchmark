#!/usr/bin/env python3
"""
Backward-compatible wrapper for the old script name.
Use download_iol.py instead.
"""

from __future__ import annotations

from download_iol import main


if __name__ == "__main__":
    raise SystemExit(main())
