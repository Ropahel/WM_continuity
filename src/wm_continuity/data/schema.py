"""Canonical Arrow schemas for the raw per-run recording streams."""

import pyarrow as pa

SCHEMA_VERSION = 1

FRAMES_SCHEMA = pa.schema(
    [
        pa.field("run_id", pa.string(), nullable=False),
        pa.field("frame_idx", pa.int64(), nullable=False),
        pa.field("t_capture_ns", pa.int64(), nullable=False),
        pa.field("image_path", pa.string(), nullable=True),
        pa.field("width", pa.int32(), nullable=True),
        pa.field("height", pa.int32(), nullable=True),
        pa.field("capture_ok", pa.bool_(), nullable=False),
    ]
)

TELEMETRY_SCHEMA = pa.schema(
    [
        pa.field("run_id", pa.string(), nullable=False),
        pa.field("telemetry_idx", pa.int64(), nullable=False),
        pa.field("t_receive_ns", pa.int64(), nullable=False),
        pa.field("speed", pa.float32(), nullable=True),
        pa.field("steer", pa.float32(), nullable=True),
        pa.field("gas", pa.float32(), nullable=True),
        pa.field("brake", pa.float32(), nullable=True),
        pa.field("gear", pa.int16(), nullable=True),
        pa.field("rpm", pa.float32(), nullable=True),
        pa.field("valid", pa.bool_(), nullable=False),
    ]
)

ACTIONS_SCHEMA = pa.schema(
    [
        pa.field("run_id", pa.string(), nullable=False),
        pa.field("action_idx", pa.int64(), nullable=False),
        pa.field("t_issue_ns", pa.int64(), nullable=False),
        pa.field("t_effective_ns", pa.int64(), nullable=True),
        pa.field("steer", pa.float32(), nullable=False),
        pa.field("gas", pa.float32(), nullable=False),
        pa.field("brake", pa.float32(), nullable=False),
        pa.field("source", pa.string(), nullable=False),
    ]
)
