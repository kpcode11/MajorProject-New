# Passive Bot Guard (SIH1672)

Passive Bot Guard is a student-project prototype for privacy-preserving,
behaviour-based bot detection as an alternative to CAPTCHA. It is designed only
for a local mock portal; it is not a government service or a production system.

The project will combine mouse and keyboard timing/trajectory features with a
small environment rule layer. It never stores typed characters, key identities,
form values, or persistent device identifiers.

## Current status

Phase 0 scaffolding is complete. Phase 1 will inspect the configured public
datasets before any loader or model is written. No model results exist yet.

## Development setup

Use Python 3.11 or later on Windows. Dataset inputs must remain read-only outside
the repository; copy `config/datasets.example.yaml` to the ignored
`config/datasets.local.yaml` only when configuring another machine.

```powershell
python scripts/tasks.py setup
python scripts/tasks.py lint
python scripts/tasks.py test-fast
python scripts/status.py
```

See [the master plan](docs/MASTER_PLAN.md) for phased work, and read
[AGENTS.md](AGENTS.md) before making repository changes.
