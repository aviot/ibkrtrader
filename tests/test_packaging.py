from pathlib import Path


def test_windows_spec_targets_pyw_launcher() -> None:
    spec = Path("packaging/windows/ibkr-shell.spec").read_text()

    assert "launch_gui.pyw" in spec
    assert "console=False" in spec
    assert "name='ibkr-shell'" in spec


def test_windows_build_script_mentions_pyinstaller() -> None:
    script = Path("scripts/build_windows.py").read_text()

    assert "PyInstaller" in script
    assert "pip install .[build,gui,ibkr]" in script
