import pytest
from school_lab.timing import timed


def test_timing_preserves_metadata_and_result():
    @timed
    def add(a: int, b: int) -> int:
        """Сложение."""
        return a + b

    assert add(2, 3) == 5
    assert add.__name__ == "add"
    assert add.__doc__ == "Сложение."
    assert add.__wrapped__(2, 3) == 5
    assert add.last_seconds >= 0


def test_timing_also_records_failure():
    @timed
    def crash() -> None:
        raise ValueError("test")

    with pytest.raises(ValueError):
        crash()
    assert crash.last_seconds >= 0
