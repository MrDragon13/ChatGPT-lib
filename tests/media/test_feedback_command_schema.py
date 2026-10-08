from media.commands.schema import parse_command


VALID_UUID = "123e4567-e89b-42d3-a456-426614174000"


def test_edit_feedback_operation_is_registered():
    command = parse_command({
        "schema_version": 1,
        "operation_id": VALID_UUID,
        "operation": "edit_viewing_feedback",
        "work_ref": {"id": "arrival-2016"},
        "target_edits": [{"target": "primary", "clear": ["rating"]}],
    })
    assert type(command).__name__ == "EditViewingFeedbackCommand"
