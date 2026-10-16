from wm_continuity.data.schema import (
    ACTIONS_SCHEMA,
    FRAMES_SCHEMA,
    SCHEMA_VERSION,
    TELEMETRY_SCHEMA,
)


def test_raw_schemas_have_unique_field_names() -> None:
    for schema in (FRAMES_SCHEMA, TELEMETRY_SCHEMA, ACTIONS_SCHEMA):
        assert len(schema.names) == len(set(schema.names))


def test_frames_schema_keeps_image_bytes_out_of_parquet() -> None:
    assert FRAMES_SCHEMA.names == [
        "run_id",
        "frame_idx",
        "t_capture_ns",
        "image_path",
        "width",
        "height",
        "capture_ok",
    ]


def test_telemetry_schema_contains_requested_signals() -> None:
    assert {
        "speed",
        "steer",
        "gas",
        "brake",
        "gear",
        "rpm",
    }.issubset(TELEMETRY_SCHEMA.names)
    assert TELEMETRY_SCHEMA.field("speed").nullable
    assert TELEMETRY_SCHEMA.field("gear").nullable


def test_actions_schema_distinguishes_issue_and_effective_time() -> None:
    assert ACTIONS_SCHEMA.field("t_issue_ns").nullable is False
    assert ACTIONS_SCHEMA.field("t_effective_ns").nullable is True


def test_schema_version_is_positive() -> None:
    assert SCHEMA_VERSION >= 1
