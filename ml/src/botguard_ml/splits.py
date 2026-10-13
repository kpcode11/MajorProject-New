"""Leakage-safe grouped dataset split utilities."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from random import Random
from typing import Any

Row = Mapping[str, Any]
Indices = tuple[list[int], list[int]]


def _validate_rows(rows: Sequence[Row]) -> None:
    required = {"split_group", "label", "dataset", "domain", "bot_type"}
    for index, row in enumerate(rows):
        missing = required.difference(row)
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(f"row {index} is missing required metadata: {names}")
        if not str(row["split_group"]):
            raise ValueError(f"row {index} has an empty split_group")


def _partition_by_groups(rows: Sequence[Row], test_groups: set[str]) -> Indices:
    test = [index for index, row in enumerate(rows) if str(row["split_group"]) in test_groups]
    train = [index for index in range(len(rows)) if index not in set(test)]
    if not train or not test:
        raise ValueError("split produced an empty train or test partition")
    return train, test


def grouped_split(
    rows: Sequence[Row],
    *,
    test_size: float = 0.2,
    seed: int = 42,
) -> Indices:
    """Split rows by ``split_group`` so no group crosses train and test."""
    _validate_rows(rows)
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between zero and one")
    groups = sorted({str(row["split_group"]) for row in rows})
    if len(groups) < 2:
        raise ValueError("at least two split groups are required")
    shuffled = groups[:]
    Random(seed).shuffle(shuffled)
    n_test = max(1, min(len(groups) - 1, round(len(groups) * test_size)))
    return _partition_by_groups(rows, set(shuffled[:n_test]))


def _fixed_partition(
    rows: Sequence[Row],
    *,
    field: str,
    test_value: str,
) -> Indices:
    _validate_rows(rows)
    test_groups = {str(row["split_group"]) for row in rows if str(row[field]) == test_value}
    if not test_groups:
        raise ValueError(f"no rows found for {field}={test_value!r}")
    train_groups = {str(row["split_group"]) for row in rows if str(row[field]) != test_value}
    if train_groups.intersection(test_groups):
        raise ValueError("a split_group contains multiple partition values")
    return _partition_by_groups(rows, test_groups)


def cross_phase_split(
    rows: Sequence[Row],
    *,
    test_phase: str = "wiki_part2",
) -> Indices:
    """Train on one Bournemouth phase and test on the other phase."""
    return _fixed_partition(rows, field="domain", test_value=test_phase)


def cross_dataset_split(
    rows: Sequence[Row],
    *,
    test_dataset: str,
) -> Indices:
    """Train on all datasets except ``test_dataset`` and test on it."""
    return _fixed_partition(rows, field="dataset", test_value=test_dataset)


def leave_one_bot_type_out(
    rows: Sequence[Row],
    *,
    test_bot_type: str,
) -> Indices:
    """Train on all other bot types and test only the held-out bot type."""
    return _fixed_partition(rows, field="bot_type", test_value=test_bot_type)
