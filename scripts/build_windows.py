from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "packaging" / "windows" / "ibkr-shell.spec"
DIST = ROOT / "dist"
BUILD = ROOT / "build"
RELEASES = ROOT / "release" / "windows"
PYPROJECT = ROOT / "pyproject.toml"
WINDOWS_README = ROOT / "packaging" / "windows" / "README-windows.txt"
ICON_SCRIPT = ROOT / "packaging" / "windows" / "generate_icon.py"


def project_version() -> str:
    data = tomllib.loads(PYPROJECT.read_text())
    return data["project"]["version"]


def build_release_dir(version: str) -> Path:
    return RELEASES / f"ibkr-shell-{version}"


def main() -> int:
    pyinstaller = shutil.which("pyinstaller")
    if pyinstaller is None:
        print("PyInstaller is not installed. Install with `pip install .[build,gui,ibkr]`.")
        return 1

    subprocess.run([sys.executable, str(ICON_SCRIPT)], cwd=ROOT, check=True)

    version = project_version()
    release_dir = build_release_dir(version)
    if release_dir.exists():
        shutil.rmtree(release_dir)

    command = [
        pyinstaller,
        "--noconfirm",
        "--clean",
        str(SPEC),
    ]
    print("Running:", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)

    built_app = DIST / "ibkr-shell"
    shutil.copytree(built_app, release_dir)
    shutil.copy2(ROOT / "README.md", release_dir / "README.md")
    shutil.copy2(WINDOWS_README, release_dir / "README-windows.txt")

    archive = shutil.make_archive(str(release_dir), "zip", root_dir=release_dir.parent, base_dir=release_dir.name)
    print(f"Build complete. Release folder: {release_dir}")
    print(f"Zip archive: {archive}")
    print(f"Intermediate build dir: {BUILD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
