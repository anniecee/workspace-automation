"""Executable entrypoint when invoked as `python -m {{package_name}}`."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
