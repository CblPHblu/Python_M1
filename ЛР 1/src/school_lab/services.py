from dataclasses import dataclass, field, asdict
from typing import Literal
from .models import AnalysisContext, AnalysisReport
from .errors import SubmissionError, AnalysisFailure
from .parsing import parse_submission
from .hashing import submission_hash
from .repositories import SubmissionRepository
from .sources import SubmissionSource
from .analyzers import AnalyzerRegistry, validate_report

@dataclass(frozen=True, slots=True)
class Acceptance:
    status: Literal["accepted", "duplicate"]
    submission_id: str
    content_hash: str

class SubmissionService:
    def __init__(self, repository: SubmissionRepository) -> None:
        self.repository = repository

    def accept(self, raw: object) -> Acceptance:
        value = parse_submission(raw)
        digest = submission_hash(value)
        previous = self.repository.get(value.submission_id)
        if previous is not None:
            if submission_hash(previous) != digest:
                raise SubmissionError("conflict", "submission_id", "Для новой версии нужен новый submission_id")
            return Acceptance("duplicate", value.submission_id, digest)
        self.repository.add(value)
        return Acceptance("accepted", value.submission_id, digest)

@dataclass
class ImportSummary:
    accepted: list[str] = field(default_factory=list)
    duplicate: list[str] = field(default_factory=list)
    errors: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

def import_source(source: SubmissionSource, service: SubmissionService) -> ImportSummary:
    summary = ImportSummary()
    with source.open() as records:
        for record in records:
            if record.error is not None:
                summary.errors.append({"line_no": record.line_no, **record.error.to_dict()})
                continue
            try:
                result = service.accept(record.raw)
            except SubmissionError as exc:
                summary.errors.append({"line_no": record.line_no, **exc.to_dict()})
            else:
                (summary.accepted if result.status == "accepted" else summary.duplicate).append(result.submission_id)
    return summary

class AnalysisService:
    def __init__(self, repository: SubmissionRepository, registry: AnalyzerRegistry) -> None:
        self.repository = repository
        self.registry = registry

    def run(self, submission_id: str, analyzer_name: str, context: AnalysisContext) -> AnalysisReport:
        value = self.repository.get(submission_id)
        if value is None:
            raise AnalysisFailure("Сначала нужно принять сдачу")
        if value.assignment_id != context.assignment.assignment_id:
            raise AnalysisFailure("Контекст относится к другому заданию")
        analyzer = self.registry.create(analyzer_name)
        try:
            report = analyzer.analyze(value, context)
        except AnalysisFailure:
            raise
        except Exception as exc:
            raise AnalysisFailure(f"Ошибка анализатора {analyzer_name}: {type(exc).__name__}") from exc
        validate_report(report, value, context)
        if report.analyzer_id != analyzer.analyzer_id or report.analyzer_version != analyzer.analyzer_version:
            raise AnalysisFailure("Версия или ID отчёта не соответствует анализатору")
        return report
