"""Tests for the DELBOT-Mouse trajectory representation."""

from io import StringIO

from botguard_ml.loaders.delbot_mouse import canonical_events


def test_parses_human_trajectory_and_relative_timestamps() -> None:
    lines = iter(
        StringIO(
            "resolution:1920,1080\n100.0,Pressed,10,20\n110.0,Move,12,22\n120.0,Released,12,22\n"
        )
        .read()
        .splitlines()
    )

    events = canonical_events(lines, session_id="human-1", source="circles_human_pc1/a.txt")

    assert [event["event"] for event in events] == ["down", "move", "up"]
    assert [event["t_ms"] for event in events] == [0.0, 10.0, 20.0]
    assert events[0]["screen_w"] == 1920.0
    assert events[0]["label"] == 0
    assert events[0]["bot_type"] == "human"


def test_maps_touch_events_and_bot_subjects() -> None:
    lines = iter(StringIO("resolution:100,200\n1.0,PressedTouch,3,4\n").read().splitlines())

    events = canonical_events(lines, session_id="bot-1", source="circles_bot_pynput/a.txt")

    assert events[0]["event"] == "down"
    assert events[0]["touchscreen"] is True
    assert events[0]["label"] == 1
    assert events[0]["bot_type"] == "pynput"
    assert events[0]["subject_id"] == "pynput:bot-1"
