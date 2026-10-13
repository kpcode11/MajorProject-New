"""Tests for parsing the observed Bournemouth mouse-session representations."""

from pathlib import Path

from botguard_ml.loaders.web_bot_detection import (
    canonical_events,
    concatenated_objects,
    parse_pairs,
    parse_times,
)


def test_parses_aligned_phase1_movement_series() -> None:
    """Coordinate and timestamp strings become relative-time canonical events."""
    record = {
        "session_id": "session-a",
        "mousemove_total_behaviour": "[1,2][m(3,4)]",
        "mousemove_times": "100,125",
    }
    events = canonical_events(record, label=0, bot_type="human", domain="wiki_part1")
    assert parse_pairs(record["mousemove_total_behaviour"]) == [(1.0, 2.0), (3.0, 4.0)]
    assert parse_times(record["mousemove_times"]) == [100.0, 125.0]
    assert [event["t_ms"] for event in events] == [0.0, 25.0]
    assert {event["event"] for event in events} == {"move"}
    assert {event["subject_id"] for event in events} == {"session-a"}


def test_streams_concatenated_json_objects() -> None:
    """MongoDB-style adjacent objects are decoded without an enclosing array."""
    source = Path(__file__).parent / "fixtures" / "concatenated_objects.json"
    session_ids = [item["session_id"] for item in concatenated_objects(source, chunk_size=7)]
    assert session_ids == ["a", "b"]
