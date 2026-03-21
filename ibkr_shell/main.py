from __future__ import annotations

import sys

from .config import AppConfig
from .gui import launch


def main() -> int:
    config = AppConfig.from_env()
    try:
        return launch(config, sys.argv)
    except RuntimeError as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
