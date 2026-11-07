import copy
from dataclasses import asdict
import pytest
from school_lab.parsing import parse_submission, decode_json
from school_lab.errors import SubmissionError

@pytest.mark.parametrize("field,value", [
    ("student_id", " "), ("schema_version", True), ("schema_version", "1"),
    ("submitted_at", "2026-10-01T10:00:00"), ("submitted_at", "broken"),
    ("code", 15), ("text", None), ("template_id", " "),
])
def test_invalid_field(valid, field, value):
    valid[field] = value
    with pytest.raises(SubmissionError):
        parse_submission(valid)

def test_unknown_field(valid):
    valid["unknown"] = 1
    with pytest.raises(SubmissionError, match="Неизвестное"):
        parse_submission(valid)

def test_missing_field(valid):
    del valid["student_id"]
    with pytest.raises(SubmissionError) as err:
        parse_submission(valid)
    assert err.value.field == "student_id"

def test_ai_declaration(valid):
    valid["ai_declaration"] = {"used":True,"tool":None,"purpose":None,"verified_by_student":True}
    with pytest.raises(SubmissionError):
        parse_submission(valid)

def test_ai_unknown_field(valid):
    valid["ai_declaration"]["extra"] = 1
    with pytest.raises(SubmissionError):
        parse_submission(valid)

def test_empty_payload(valid):
    valid["text"] = " "
    valid["code"] = "\n"
    with pytest.raises(SubmissionError):
        parse_submission(valid)

def test_unsupported_version(valid):
    valid["schema_version"] = 2
    with pytest.raises(SubmissionError) as err:
        parse_submission(valid)
    assert err.value.code == "unsupported_version"

def test_original_unchanged(valid):
    original = copy.deepcopy(valid)
    model = parse_submission(valid)
    assert valid == original
    assert asdict(model) == original

def test_invalid_json_and_repeated_keys():
    for line in ("{broken", '{"a":1,"a":2}', "NaN"):
        with pytest.raises(SubmissionError) as err:
            decode_json(line)
        assert err.value.code == "invalid_json"
