"""Cross-platform task runner for the passive bot-detection project."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = (ROOT / "ml", ROOT / "backend")
IMPLEMENTED = ("setup", "lint", "test", "test-fast", "status", "data-audit", "fingerprint")
PLANNED = ("train-mouse", "train-keyboard", "train-touch", "eval-all", "serve", "demo", "loadtest")


def package_python(package: Path) -> Path:
    """Return the Windows Python executable for a package-local environment."""
    return package / ".venv" / "Scripts" / "python.exe"


def run(command: list[str], cwd: Path = ROOT) -> None:
    """Run a command and raise immediately when it fails."""
    subprocess.run(command, cwd=cwd, check=True)


def require_environment(package: Path) -> Path:
    """Return a package interpreter or explain how to create it."""
    interpreter = package_python(package)
    if not interpreter.exists():
        raise RuntimeError(f"Missing {interpreter}. Run: python scripts/tasks.py setup")
    return interpreter


def setup() -> None:
    """Create local package environments and install their development dependencies."""
    for package in PACKAGES:
        interpreter = package_python(package)
        if not interpreter.exists():
            run([sys.executable, "-m", "venv", str(package / ".venv")])
        run([str(interpreter), "-m", "pip", "install", "-e", ".[dev]"], cwd=package)


def lint() -> None:
    """Run Ruff checks, format checks, and strict mypy for both Python packages."""
    for package, source, tests in ((PACKAGES[0], "src", "tests"), (PACKAGES[1], "app", "tests")):
        interpreter = require_environment(package)
        run([str(interpreter), "-m", "ruff", "check", source, tests], cwd=package)
        run([str(interpreter), "-m", "ruff", "format", "--check", source, tests], cwd=package)
        run([str(interpreter), "-m", "mypy", source], cwd=package)


def test() -> None:
    """Run the complete test suites for both Python packages."""
    for package in PACKAGES:
        run(
            [str(require_environment(package)), "-m", "pytest", "-q", "-x", "--maxfail=3"],
            cwd=package,
        )


def test_fast() -> None:
    """Run the current fast tests; slow markers can be excluded here later."""
    test()


def status() -> None:
    """Print the concise repository handoff status report."""
    run([sys.executable, str(ROOT / "scripts" / "status.py")])


def data_audit() -> None:
    """Create bounded audit reports for canonical mouse Parquet shards."""
    run(
        [
            str(require_environment(PACKAGES[0])),
            str(ROOT / "scripts" / "data_audit.py"),
            "--input-root",
            str(ROOT / "data" / "interim"),
            "--output-root",
            str(ROOT / "results" / "mouse"),
        ]
    )


def fingerprint() -> None:
    """Run the human-only cross-dataset fingerprint experiment."""
    run(
        [
            str(require_environment(PACKAGES[0])),
            str(ROOT / "scripts" / "dataset_fingerprint.py"),
            "--input-root",
            str(ROOT / "data" / "interim"),
            "--output",
            str(ROOT / "results" / "mouse" / "fingerprint.json"),
        ]
    )


def main() -> int:
    """Parse a task command and dispatch it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=(*IMPLEMENTED, *PLANNED))
    command = parser.parse_args().command
    try:
        if command == "setup":
            setup()
        elif command == "lint":
            lint()
        elif command in {"test", "test-fast"}:
            test_fast() if command == "test-fast" else test()
        elif command == "status":
            status()
        elif command == "data-audit":
            data_audit()
        elif command == "fingerprint":
            fingerprint()
        else:
            print(f"{command}: not implemented yet")
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"tasks: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
