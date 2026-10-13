## 3. Conventions, tooling and Windows environment

### 3.1 Windows specifics

- Use PowerShell commands in documentation. Activate venvs with `.venv\Scripts\Activate.ps1`.
- Use `pathlib.Path` everywhere; never hard-code backslashes in code. Dataset paths come from `config/datasets.local.yaml`.
- `make` is not assumed. Use `python scripts/tasks.py <command>` (same commands as the Makefile targets: `setup`, `lint`, `test`, `test-fast`, `data-audit`, `train-mouse`, `train-keyboard`, `train-touch`, `eval-all`, `serve`, `demo`, `loadtest`, `status`).
- Long paths: the IEEE dataset folder name is long. If a path that exists raises `FileNotFoundError`, retry with the extended-length prefix (`\\?\C:\...`) or ask the human to enable Windows long paths.
- Add `.gitattributes` with `* text=auto` to avoid line-ending churn between tools.
- Do not place the repository inside OneDrive-synced folders.
- Docker is **optional**. Default dev runs use the in-memory store and SQLite. Redis/PostgreSQL via Docker Desktop or WSL2 are used only when the human asks for the production-like profile.
- Ask the human once (P0-03) for RAM, free disk, CPU cores, Python/Node versions and record them in `docs/env.md`.

### 3.2 Python

- Python 3.11+ (use what is installed if 3.10+ and note it). `pyproject.toml` per package (`ml`, `backend`). `ruff` for lint and format; `mypy` on library code.
- Type hints and docstrings with units (milliseconds, pixels).
- Single seed constant (`SEED = 42`) passed explicitly to splitters, models and generators.
- Config in YAML (`ml/configs/`, `backend/config/`); secrets only through environment variables.
- Use `logging`, not `print`, in library code.

### 3.3 TypeScript

`strict: true`, ESLint, Prettier, vitest. Build with Vite/Rollup to ES module and UMD. No runtime dependencies in the SDK core.

### 3.4 Git

Branch per phase; Conventional commit prefixes plus task ID (`feat:` etc. optional, the task ID is mandatory); small commits; never force-push.

### 3.5 Units

Time in **milliseconds** (float). Coordinates in pixels where real, and flagged `coord_space` when normalised (`pixels`, `norm01`, `grid200`). Missing values are `NaN`; each modality has a `has_<modality>` flag.

---
