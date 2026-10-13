"""Split the master plan into per-phase and appendix Markdown files."""

from __future__ import annotations

import pathlib
import re


def main() -> None:
    """Write small plan sections that low-budget agents can load selectively."""
    root = pathlib.Path(__file__).resolve().parents[1]
    text = (root / "docs" / "MASTER_PLAN.md").read_text(encoding="utf-8")
    output_dir = root / "docs" / "plan"
    output_dir.mkdir(parents=True, exist_ok=True)

    index: list[str] = []
    for index_number, section in enumerate(re.split(r"(?m)^(?=## )", text)):
        first_line = section.split("\n", 1)[0]
        phase_match = re.match(r"## Phase (\d+)", first_line)
        appendix_match = re.match(r"## Appendix ([A-G])", first_line)
        numbered_match = re.match(r"## (\d+)\.", first_line)
        if phase_match:
            name = f"phase_{phase_match.group(1)}.md"
        elif appendix_match:
            name = f"appendix_{appendix_match.group(1).lower()}.md"
        elif numbered_match:
            name = f"section_{numbered_match.group(1)}.md"
        elif index_number == 0:
            name = "header.md"
        else:
            name = f"misc_{index_number}.md"
        (output_dir / name).write_text(section.rstrip() + "\n", encoding="utf-8")
        index.append(f"- {name}: {first_line.strip('# ').strip()}")

    (output_dir / "INDEX.md").write_text(
        "# Plan index\n\n" + "\n".join(index) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
