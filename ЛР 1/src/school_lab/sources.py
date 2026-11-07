from contextlib import contextmanager, AbstractContextManager
from dataclasses import dataclass
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol
import copy
from .errors import SubmissionError
from .parsing import decode_json

@dataclass(frozen=True, slots=True)
class SourceRecord:
    line_no: int
    raw: object = None
    error: SubmissionError | None = None

class SubmissionSource(Protocol):
    def open(self) -> AbstractContextManager[Iterator[SourceRecord]]: ...

class InMemorySource:
    def __init__(self, values: list[object]) -> None:
        self._values = copy.deepcopy(values)

    @contextmanager
    def open(self) -> Iterator[Iterator[SourceRecord]]:
        def records() -> Iterator[SourceRecord]:
            for number, raw in enumerate(self._values, 1):
                yield SourceRecord(number, copy.deepcopy(raw))
        yield records()

class JSONLSource:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.last_closed: bool | None = None

    @contextmanager
    def open(self) -> Iterator[Iterator[SourceRecord]]:
        handle = self.path.open("r", encoding="utf-8")
        try:
            with handle:
                def records() -> Iterator[SourceRecord]:
                    for number, line in enumerate(handle, 1):
                        try:
                            raw = decode_json(line)
                        except SubmissionError as exc:
                            yield SourceRecord(number, error=exc)
                        else:
                            yield SourceRecord(number, raw=raw)
                yield records()
        finally:
            self.last_closed = handle.closed
