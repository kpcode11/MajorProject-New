# Development environment

**Recorded:** 2026-10-13
**Source:** Human-reported system details.

| Item | Value |
|---|---|
| RAM | 16 GB |
| CPU | 16 cores; 24 logical processors |
| Free disk, C: | 84.9 GB |
| Free disk, D: | 181 GB |
| Python | 3.14.7 |
| Node.js | 24.20.0 |
| Docker | 29.8.2 (build `7fc2dff`) reported; CLI is not on the current shell `PATH` |
| WSL | Installed |
| Git | 2.55.0.windows.5 |
| Git clone | Works on this laptop |

## Project limits

- Dataset inputs remain read-only under the configured datasets root.
- The default process memory limit is 6 GB, leaving headroom for the operating
  system and other tools on this 16 GB machine.
- Any task projected to write more than 5 GB, or run with less than 10 GB free
  disk space, requires human approval.
