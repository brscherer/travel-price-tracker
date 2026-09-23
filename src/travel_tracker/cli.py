from __future__ import annotations

import logging
import sys

from .promo_scan import run_promo_scan
from .scan import run_scan
from .wide_scan import run_wide_scan

_COMMANDS = {
    "scan": run_scan,
    "wide-scan": run_wide_scan,
    "promo-scan": run_promo_scan,
}


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if len(sys.argv) < 2 or sys.argv[1] not in _COMMANDS:
        print(f"Usage: python -m travel_tracker <{'|'.join(_COMMANDS)}>")
        sys.exit(1)

    _COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()
