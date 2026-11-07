import copy
from pathlib import Path
import pytest
from school_lab.errors import SubmissionError
from school_lab.repositories import InMemorySubmissionRepository
from school_lab.sources import InMemorySource, JSONLSource
from school_lab.services import SubmissionService, import_source

def test_accepted_duplicate_conflict(valid):
    repo = InMemorySubmissionRepository()
    service = SubmissionService(repo)
    assert service.accept(valid).status == "accepted"
    assert service.accept(copy.deepcopy(valid)).status == "duplicate"
    changed = copy.deepcopy(valid)
    changed["text"] += "другое"
    with pytest.raises(SubmissionError) as err:
        service.accept(changed)
    assert err.value.code == "conflict"
    assert len(repo) == 1
    assert repo.get(valid["submission_id"]).text == valid["text"]

@pytest.mark.parametrize("source_type", ["memory", "file"])
def test_source_contract(valid, tmp_path, source_type):
    import json
    if source_type == "memory":
        source = InMemorySource([valid, valid])
    else:
        path = tmp_path / "data.jsonl"
        path.write_text("\n".join(json.dumps(valid) for _ in range(2)),encoding="utf-8")
        source = JSONLSource(path)
    with source.open() as rows:
        loaded = list(rows)
    assert [r.line_no for r in loaded] == [1,2]
    assert [r.raw for r in loaded] == [valid,valid]
    result = import_source(source,SubmissionService(InMemorySubmissionRepository()))
    assert result.accepted == [valid["submission_id"]]
    assert result.duplicate == [valid["submission_id"]]


def test_import_continues_after_invalid_json(tmp_path, valid):
    import json
    path = tmp_path / "mixed.jsonl"
    other = copy.deepcopy(valid)
    other["submission_id"] = "second"
    path.write_text(json.dumps(valid) + "\n{broken\n" + json.dumps(other) + "\n",encoding="utf-8")
    summary = import_source(JSONLSource(path), SubmissionService(InMemorySubmissionRepository()))
    assert summary.accepted == [valid["submission_id"], "second"]
    assert summary.errors[0]["line_no"] == 2
    assert summary.errors[0]["code"] == "invalid_json"

def test_file_closed_on_early_exit_and_exception(tmp_path, valid):
    import json
    path = tmp_path / "file.jsonl"
    path.write_text(json.dumps(valid) + "\n" + json.dumps(valid), encoding="utf-8")
    source = JSONLSource(path)
    with source.open() as rows:
        next(rows)
    assert source.last_closed is True
    with pytest.raises(RuntimeError):
        with source.open() as rows:
            next(rows)
            raise RuntimeError("stop")
    assert source.last_closed is True
