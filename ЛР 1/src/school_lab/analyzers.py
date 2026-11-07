from datetime import datetime, timezone
from dataclasses import asdict
from typing import Protocol, Callable
from uuid import uuid4
import math
from .models import Submission, AnalysisContext, AnalysisReport, Finding, Evidence
from .errors import AnalysisFailure
from .hashing import stable_hash, submission_hash

class Analyzer(Protocol):
    analyzer_id: str
    analyzer_version: str
    def analyze(self, submission: Submission, context: AnalysisContext) -> AnalysisReport: ...

def make_report(submission: Submission, context: AnalysisContext, analyzer_id: str,
                analyzer_version: str, findings: tuple[Finding, ...],
                review_required: bool = False) -> AnalysisReport:
    return AnalysisReport(str(uuid4()), submission.submission_id, submission_hash(submission),
                          analyzer_id, analyzer_version, stable_hash(context.config_payload()),
                          findings, datetime.now(timezone.utc).isoformat(), review_required)

def validate_report(report: AnalysisReport, submission: Submission, context: AnalysisContext) -> None:
    if not isinstance(report, AnalysisReport):
        raise AnalysisFailure("Анализатор должен вернуть AnalysisReport")
    if report.submission_id != submission.submission_id or report.submission_hash != submission_hash(submission):
        raise AnalysisFailure("Отчёт относится к другой версии работы")
    if report.config_hash != stable_hash(context.config_payload()):
        raise AnalysisFailure("Неверный хеш конфигурации")
    if not all(isinstance(x, str) and x.strip() for x in (report.report_id, report.analyzer_id, report.analyzer_version)):
        raise AnalysisFailure("Отсутствует идентификатор отчёта или анализатора")
    if type(report.review_required) is not bool:
        raise AnalysisFailure("review_required должен быть bool")
    try:
        timestamp = datetime.fromisoformat(report.created_at)
    except (ValueError, TypeError) as exc:
        raise AnalysisFailure("Неверный timestamp отчёта") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise AnalysisFailure("В отчёте нужен часовой пояс")
    if not isinstance(report.findings, tuple):
        raise AnalysisFailure("findings должен быть tuple")
    for finding in report.findings:
        if not isinstance(finding, Finding) or finding.kind not in {"similarity", "rubric_feedback", "processing_error"}:
            raise AnalysisFailure("Неверный finding")
        if finding.score is not None and (type(finding.score) not in (int, float) or not math.isfinite(finding.score) or not 0 <= finding.score <= 1):
            raise AnalysisFailure("score должен быть от 0 до 1 либо None")
        if not isinstance(finding.explanation, str) or not finding.explanation.strip():
            raise AnalysisFailure("Необходимо пояснение")
        for item in finding.evidence:
            if not isinstance(item, Evidence) or item.submission_id != submission.submission_id or item.field not in ("text", "code"):
                raise AnalysisFailure("Неверная ссылка evidence")
            length = len(getattr(submission, item.field).splitlines())
            if type(item.start_line) is not int or type(item.end_line) is not int or not (1 <= item.start_line <= item.end_line <= length):
                raise AnalysisFailure("Evidence выходит за пределы исходника")

class LengthAnalyzer:
    analyzer_id = "length"
    analyzer_version = "1.0"

    def analyze(self, submission: Submission, context: AnalysisContext) -> AnalysisReport:
        text_lines = [i for i, line in enumerate(submission.text.splitlines(), 1) if line.strip()]
        code_lines = [i for i, line in enumerate(submission.code.splitlines(), 1) if line.strip()]
        evidence = tuple(Evidence(submission.submission_id, field, n, n)
                         for field, numbers in (("text", text_lines), ("code", code_lines)) for n in numbers)
        finding = Finding("rubric_feedback", None, evidence,
                          f"Непустые строки: text={len(text_lines)}, code={len(code_lines)}. Длина не показывает правильность решения.")
        return make_report(submission, context, self.analyzer_id, self.analyzer_version, (finding,))

def template_ranges(code: str, template: str) -> tuple[tuple[int, int], ...]:
    if not template.strip():
        return ()
    lines, expected = code.splitlines(), template.splitlines()
    width = len(expected)
    return tuple((i + 1, i + width) for i in range(len(lines) - width + 1)
                 if lines[i:i+width] == expected)

class TemplateAnalyzer:
    analyzer_id = "template"
    analyzer_version = "1.0"

    def analyze(self, submission: Submission, context: AnalysisContext) -> AnalysisReport:
        if submission.assignment_id != context.assignment.assignment_id:
            raise AnalysisFailure("Контекст другого задания")
        ranges = template_ranges(submission.code, context.assignment.allowed_template)
        evidence = tuple(Evidence(submission.submission_id, "code", start, end) for start, end in ranges)
        message = (f"Найдено {len(ranges)} разрешённых совпадений шаблона; это не нарушение."
                   if ranges else "Точного совпадения с разрешённым шаблоном нет.")
        return make_report(submission, context, self.analyzer_id, self.analyzer_version,
                           (Finding("similarity", None, evidence, message),))

class DeclarationAnalyzer:
    """Третий анализатор для демонстрации расширяемости на защите."""
    analyzer_id = "declaration"
    analyzer_version = "1.0"

    def analyze(self, submission: Submission, context: AnalysisContext) -> AnalysisReport:
        dec = submission.ai_declaration
        message = (f"ИИ указан: {dec.tool}. Цель: {dec.purpose}." if dec.used
                   else "Использование ИИ не заявлено.")
        return make_report(submission, context, self.analyzer_id, self.analyzer_version,
                           (Finding("rubric_feedback", None, (), message),),
                           review_required=dec.used and not dec.verified_by_student)

class AnalyzerRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], Analyzer]] = {}

    def register(self, name: str, factory: Callable[[], Analyzer]) -> None:
        if not name.strip() or name in self._factories:
            raise AnalysisFailure("Имя анализатора должно быть уникальным")
        self._factories[name] = factory

    def create(self, name: str) -> Analyzer:
        if name not in self._factories:
            raise AnalysisFailure(f"Неизвестный анализатор: {name}")
        analyzer = self._factories[name]()
        if analyzer.analyzer_id != name:
            raise AnalysisFailure("Имя регистрации отличается от analyzer_id")
        return analyzer

def default_registry() -> AnalyzerRegistry:
    registry = AnalyzerRegistry()
    registry.register("length", LengthAnalyzer)
    registry.register("template", TemplateAnalyzer)
    return registry
