"""
Lexis — Entry Point
"""

import sys

from lexis.ui.app import run


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
