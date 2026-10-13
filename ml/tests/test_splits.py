"""Tests for leakage-safe mouse split utilities."""

from __future__ import annotations

import pytest

from botguard_ml.splits import (
    cross_dataset_split,
    cross_phase_split,
    grouped_split,
    leave_one_bot_type_out,
)


def _rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for group_index in range(6):
        dataset = "bournemouth" if group_index < 4 else "ieee"
        domain = "wiki_part1" if group_index % 2 == 0 else "wiki_part2"
        bot_type = "human" if group_index < 2 else f"bot_{group_index % 2}"
        for window_index in range(2):
            rows.append(
                {
                    "split_group": f"group-{group_index}",
                    "label": int(bot_type != "human"),
                    "dataset": dataset,
                    "domain": domain,
                    "bot_type": bot_type,
                    "window_index": window_index,
                }
            )
    return rows


def _assert_group_disjoint(
    rows: list[dict[str, object]], train: list[int], test: list[int]
) -> None:
    train_groups = {rows[index]["split_group"] for index in train}
    test_groups = {rows[index]["split_group"] for index in test}
    assert train_groups.isdisjoint(test_groups)
    assert set(train) | set(test) == set(range(len(rows)))


def test_grouped_split_keeps_all_windows_of_a_group_together() -> None:
    rows = _rows()
    train, test = grouped_split(rows, test_size=0.33, seed=7)

    _assert_group_disjoint(rows, train, test)
    assert {rows[index]["split_group"] for index in test}


def test_cross_phase_split_uses_requested_phase_as_test() -> None:
    rows = _rows()
    train, test = cross_phase_split(rows, test_phase="wiki_part2")

    _assert_group_disjoint(rows, train, test)
    assert {rows[index]["domain"] for index in test} == {"wiki_part2"}
    assert {rows[index]["domain"] for index in train} == {"wiki_part1"}


def test_cross_dataset_split_uses_requested_dataset_as_test() -> None:
    rows = _rows()
    train, test = cross_dataset_split(rows, test_dataset="ieee")

    _assert_group_disjoint(rows, train, test)
    assert {rows[index]["dataset"] for index in test} == {"ieee"}


def test_leave_one_bot_type_out_holds_out_only_requested_type() -> None:
    rows = _rows()
    train, test = leave_one_bot_type_out(rows, test_bot_type="bot_1")

    _assert_group_disjoint(rows, train, test)
    assert {rows[index]["bot_type"] for index in test} == {"bot_1"}
    assert all(rows[index]["bot_type"] != "bot_1" for index in train)


def test_invalid_split_inputs_are_rejected() -> None:
    with pytest.raises(ValueError, match="test_size"):
        grouped_split(_rows(), test_size=1)
    with pytest.raises(ValueError, match="no rows"):
        cross_dataset_split(_rows(), test_dataset="missing")
