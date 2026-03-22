from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "packaging" / "windows" / "ibkr-shell.spec"
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def main() -> int:
    pyinstaller = shutil.which("pyinstaller")
    if pyinstaller is None:
        print("PyInstaller is not installed. Install with `pip install .[build,gui,ibkr]`.")
        return 1

    command = [
        pyinstaller,
        "--noconfirm",
        "--clean",
        str(SPEC),
    ]
    print("Running:", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)
    print(f"Build complete. See {DIST / 'ibkr-shell'} and {BUILD}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
