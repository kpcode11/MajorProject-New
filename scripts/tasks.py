"""Cross-platform task runner for the passive bot-detection project."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = (ROOT / "ml", ROOT / "backend")
SDK = ROOT / "sdk"
PORTAL = ROOT / "portal"
IMPLEMENTED = (
    "setup",
    "lint",
    "test",
    "test-fast",
    "status",
    "data-audit",
    "fingerprint",
    "train-mouse",
    "train-keyboard",
    "keyboard-privacy",
    "serve",
)
PLANNED = ("train-touch", "eval-all", "demo", "loadtest")


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


def node_npm(pkg_dir: Path, *scripts: str) -> None:
    """Run npm scripts in ``pkg_dir``; skip with a notice when Node or dependencies are missing."""
    npm = shutil.which("npm")
    if npm is None or not (pkg_dir / "node_modules").exists():
        print(
            f"{pkg_dir.name}: skipped (install Node.js and run: python scripts/tasks.py setup)"
        )
        return
    for script in scripts:
        run([npm, "run", "--silent", script], cwd=pkg_dir)


def setup() -> None:
    """Create local package environments and install their development dependencies."""
    for package in PACKAGES:
        interpreter = package_python(package)
        if not interpreter.exists():
            run([sys.executable, "-m", "venv", str(package / ".venv")])
        run([str(interpreter), "-m", "pip", "install", "-e", ".[dev]"], cwd=package)
    backend_interpreter = package_python(PACKAGES[1])
    run(
        [
            str(backend_interpreter),
            "-m",
            "pip",
            "install",
            "--no-deps",
            "-e",
            str(ROOT / "ml"),
        ],
        cwd=PACKAGES[1],
    )
    npm = shutil.which("npm")
    if npm is not None and (SDK / "package-lock.json").exists():
        run([npm, "ci", "--no-fund", "--no-audit"], cwd=SDK)
        run([npm, "run", "--silent", "build"], cwd=SDK)
    if npm is not None and (PORTAL / "package-lock.json").exists():
        run([npm, "ci", "--no-fund", "--no-audit"], cwd=PORTAL)


def lint() -> None:
    """Run Ruff, strict mypy, and the SDK/portal ESLint/Prettier/tsc checks."""
    for package, source, tests in (
        (PACKAGES[0], "src", "tests"),
        (PACKAGES[1], "app", "tests"),
    ):
        interpreter = require_environment(package)
        run([str(interpreter), "-m", "ruff", "check", source, tests], cwd=package)
        run(
            [str(interpreter), "-m", "ruff", "format", "--check", source, tests],
            cwd=package,
        )
        run([str(interpreter), "-m", "mypy", source], cwd=package)
    node_npm(SDK, "lint", "typecheck")
    node_npm(PORTAL, "lint", "typecheck")


def test() -> None:
    """Run the complete test suites for both Python packages, the SDK, and the portal."""
    for package in PACKAGES:
        run(
            [
                str(require_environment(package)),
                "-m",
                "pytest",
                "-q",
                "-x",
                "--maxfail=3",
                "-p",
                "no:cacheprovider",
            ],
            cwd=package,
        )
    node_npm(SDK, "test")
    node_npm(PORTAL, "test")


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


def train_keyboard(stage: str, max_participants: int | None) -> None:
    """Build the privacy-safe Aalto keyboard event shards."""
    interpreter = require_environment(PACKAGES[0])
    if stage == "events":
        run(
            [
                str(interpreter),
                str(ROOT / "scripts" / "build_keyboard_events.py"),
                "--output-root",
                str(ROOT / "data" / "interim" / "aalto_keystrokes"),
                *(
                    []
                    if max_participants is None
                    else ["--max-participants", str(max_participants)]
                ),
            ]
        )
    elif stage == "features":
        run(
            [
                str(interpreter),
                str(ROOT / "scripts" / "build_keyboard_features.py"),
                "--input-root",
                str(ROOT / "data" / "interim" / "aalto_keystrokes"),
                "--output",
                str(
                    ROOT
                    / "data"
                    / "processed"
                    / "keyboard_features"
                    / "features.parquet"
                ),
            ]
        )
    elif stage == "evaluate":
        run(
            [
                str(interpreter),
                str(ROOT / "scripts" / "evaluate_keyboard.py"),
                "--input",
                str(
                    ROOT
                    / "data"
                    / "processed"
                    / "keyboard_features"
                    / "features.parquet"
                ),
                "--output",
                str(ROOT / "results" / "keyboard" / "evaluation.csv"),
            ]
        )
    elif stage == "onnx":
        run(
            [
                str(interpreter),
                str(ROOT / "scripts" / "export_keyboard_onnx.py"),
                "--input",
                str(
                    ROOT
                    / "data"
                    / "processed"
                    / "keyboard_features"
                    / "features.parquet"
                ),
                "--output-dir",
                str(ROOT / "backend" / "models" / "keyboard-v1"),
            ]
        )
    else:
        raise ValueError(
            "train-keyboard supports --stage events, features, evaluate, or onnx"
        )


def keyboard_privacy() -> None:
    """Scan all generated keyboard shards for prohibited content."""
    interpreter = require_environment(PACKAGES[0])
    run(
        [
            str(interpreter),
            str(ROOT / "scripts" / "scan_keyboard_privacy.py"),
            "--input-root",
            str(ROOT / "data" / "interim" / "aalto_keystrokes"),
        ]
    )


def train_mouse(stage: str, max_sessions: int | None) -> None:
    """Build the requested mouse training stage."""
    interpreter = require_environment(PACKAGES[0])
    if stage == "features":
        run(
            [
                str(interpreter),
                str(ROOT / "scripts" / "build_mouse_features.py"),
                "--input-root",
                str(ROOT / "data" / "interim"),
                "--output-root",
                str(ROOT / "data" / "processed" / "mouse_features"),
                *(
                    []
                    if max_sessions is None
                    else ["--max-sessions", str(max_sessions)]
                ),
            ]
        )
    elif stage == "baselines":
        run(
            [
                str(interpreter),
                str(ROOT / "scripts" / "run_mouse_baselines.py"),
                "--input-root",
                str(ROOT / "data" / "processed" / "mouse_features"),
                "--output",
                str(ROOT / "results" / "mouse" / "baselines.csv"),
            ]
        )
    elif stage == "hparams":
        run(
            [
                str(interpreter),
                str(ROOT / "scripts" / "run_mouse_hparams.py"),
                "--input-root",
                str(ROOT / "data" / "processed" / "mouse_features"),
                "--output",
                str(ROOT / "results" / "mouse" / "hparams.json"),
            ]
        )
    elif stage == "ablations":
        run(
            [
                str(interpreter),
                str(ROOT / "scripts" / "run_mouse_ablations.py"),
                "--input-root",
                str(ROOT / "data" / "processed" / "mouse_features"),
                "--output",
                str(ROOT / "results" / "mouse" / "ablations.csv"),
            ]
        )
    elif stage == "shap":
        run(
            [
                str(interpreter),
                str(ROOT / "scripts" / "run_mouse_shap.py"),
                "--input-root",
                str(ROOT / "data" / "processed" / "mouse_features"),
                "--output-root",
                str(ROOT / "results" / "mouse"),
            ]
        )
    elif stage == "onnx":
        run(
            [
                str(interpreter),
                str(ROOT / "scripts" / "export_mouse_onnx.py"),
                "--input-root",
                str(ROOT / "data" / "processed" / "mouse_features"),
                "--output-dir",
                str(ROOT / "backend" / "models" / "mouse-v1"),
            ]
        )
    else:
        raise ValueError(
            "train-mouse supports --stage features, baselines, hparams, ablations, shap, or onnx"
        )


def serve() -> None:
    """Start the FastAPI scoring and token backend via uvicorn."""
    interpreter = require_environment(PACKAGES[1])
    run(
        [
            str(interpreter),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=PACKAGES[1],
    )


def main() -> int:
    """Parse a task command and dispatch it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=(*IMPLEMENTED, *PLANNED))
    parser.add_argument("--stage", default="features")
    parser.add_argument("--max-sessions", type=int, default=None)
    parser.add_argument("--max-participants", type=int, default=None)
    args = parser.parse_args()
    command = args.command
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
        elif command == "train-keyboard":
            train_keyboard(args.stage, args.max_participants)
        elif command == "keyboard-privacy":
            keyboard_privacy()
        elif command == "train-mouse":
            train_mouse(args.stage, args.max_sessions)
        elif command == "serve":
            serve()
        else:
            print(f"{command}: not implemented yet")
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"tasks: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
