from pathlib import Path


def test_windows_spec_targets_pyw_launcher() -> None:
    spec = Path("packaging/windows/ibkr-shell.spec").read_text()

    assert "launch_gui.pyw" in spec
    assert "console=False" in spec
    assert "name='ibkr-shell'" in spec
    assert "SPEC_PATH = Path(__file__).resolve()" in spec
    assert "ROOT = WINDOWS_PACKAGING.parent.parent" in spec


def test_windows_build_script_mentions_pyinstaller() -> None:
    script = Path("scripts/build_windows.py").read_text()

    assert "PyInstaller" in script
    assert "pip install .[build,gui,ibkr]" in script


def test_windows_spec_includes_icon_and_version_info() -> None:
    spec = Path("packaging/windows/ibkr-shell.spec").read_text()

    assert "ibkr-shell.ico" in spec
    assert "version_info.txt" in spec


def test_icon_generator_script_exists() -> None:
    script = Path("packaging/windows/generate_icon.py").read_text()

    assert "write_icon" in script
    assert "Generated Windows icon" in script


def test_build_script_creates_release_zip() -> None:
    script = Path("scripts/build_windows.py").read_text()

    assert 'RELEASES = ROOT / "release" / "windows"' in script
    assert "make_archive" in script
    assert "README-windows.txt" in script
    assert "generate_icon.py" in script
