import copy
import json
from pathlib import Path
import pytest

@pytest.fixture
def valid() -> dict[str, object]:
    path = Path(__file__).parent.parent / "data" / "submissions.jsonl"
    return json.loads(path.read_text(encoding="utf-8").splitlines()[0])
