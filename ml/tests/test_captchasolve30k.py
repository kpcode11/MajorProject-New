"""Tests for CaptchaSolve30k decoding and canonical conversion."""

import base64
import struct
from pathlib import Path

from botguard_ml.loaders.captchasolve30k import canonical_events, decode_input_stream


def test_decodes_nine_byte_input_samples() -> None:
    payload = b"".join(
        (
            struct.pack("<ffB", 1.5, 2.5, 0),
            struct.pack("<ffB", 3.5, 4.5, 1),
        )
    )

    assert decode_input_stream(base64.b64encode(payload).decode()) == [
        (1.5, 2.5, 0),
        (3.5, 4.5, 1),
    ]


def test_canonical_events_keep_game_type_and_touchscreen() -> None:
    source = Path("fixture.json")
    payload = base64.b64encode(struct.pack("<ffB", 10.0, 20.0, 0)).decode()
    events = canonical_events(
        {
            "gameType": "sheep-herding",
            "touchscreen": True,
            "inputStream": payload,
        },
        session_id="train/7",
        source=source,
    )

    assert events[0]["coord_space"] == "grid200"
    assert events[0]["domain"] == "game_task"
    assert events[0]["game_type"] == "sheep-herding"
    assert events[0]["touchscreen"] is True
    assert events[0]["label"] == 0
    assert events[0]["bot_type"] == "human"
