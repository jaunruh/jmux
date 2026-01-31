import subprocess
import sys
import tempfile
from pathlib import Path


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "jmux.cli", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "jmux" in result.stdout
    assert "generate" in result.stdout


def test_cli_generate_help():
    result = subprocess.run(
        [sys.executable, "-m", "jmux.cli", "generate", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--root" in result.stdout


def test_cli_generate_no_models():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "empty.py"
        test_file.write_text("x = 1\n")

        result = subprocess.run(
            [sys.executable, "-m", "jmux.cli", "generate", "--root", tmpdir],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "No StreamableBaseModel subclasses found" in result.stdout


def test_cli_generate_with_model():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "models.py"
        test_file.write_text("""
from jmux import StreamableBaseModel

class TestModel(StreamableBaseModel):
    name: str
    age: int
""")

        result = subprocess.run(
            [sys.executable, "-m", "jmux.cli", "generate", "--root", tmpdir],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Found 1 model(s)" in result.stdout
        assert "TestModel" in result.stdout


def test_cli_no_command():
    result = subprocess.run(
        [sys.executable, "-m", "jmux.cli"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower() or "jmux" in result.stdout
