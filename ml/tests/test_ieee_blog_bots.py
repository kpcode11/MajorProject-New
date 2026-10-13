"""Tests for the observed IEEE blog-bots session representation."""

import json
from pathlib import Path

from botguard_ml.loaders.ieee_blog_bots import canonical_events


def test_keeps_move_click_and_scroll_events_without_dom_content() -> None:
    source = Path(__file__).parent / "fixtures" / "ieee_session.json"
    record = json.loads(source.read_text(encoding="utf-8"))

    events = canonical_events(record, session_id="train/bot_Humanish_00", source=source)

    assert [event["event"] for event in events] == ["move", "move", "click", "scroll"]
    assert [event["t_ms"] for event in events] == [10.0, 20.0, 30.0, 40.0]
    assert {event["label"] for event in events} == {1}
    assert {event["bot_type"] for event in events} == {"humanish"}
    assert {event["subject_id"] for event in events} == {"humanish:train/bot_Humanish_00"}
    assert all("text" not in event and "target" not in event for event in events)


def test_human_session_has_human_label_and_relative_time() -> None:
    source = Path(__file__).parent / "fixtures" / "ieee_session.json"
    record = json.loads(source.read_text(encoding="utf-8"))
    record["bot_info"] = None

    events = canonical_events(record, session_id="test/human_00", source=source)

    assert {event["label"] for event in events} == {0}
    assert {event["bot_type"] for event in events} == {"human"}
    assert {event["subject_id"] for event in events} == {"test/human_00"}
