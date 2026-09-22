from __future__ import annotations

import logging
import sys

from .scan import run_scan


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if len(sys.argv) < 2 or sys.argv[1] != "scan":
        print("Usage: python -m travel_tracker scan")
        sys.exit(1)

    run_scan()


if __name__ == "__main__":
    main()
