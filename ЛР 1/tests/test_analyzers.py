from dataclasses import replace
import pytest
from school_lab.analyzers import (LengthAnalyzer, TemplateAnalyzer, DeclarationAnalyzer,
    AnalyzerRegistry, default_registry, validate_report, template_ranges)
from school_lab.models import Assignment, AnalysisContext
from school_lab.parsing import parse_submission
from school_lab.repositories import InMemorySubmissionRepository
from school_lab.services import SubmissionService, AnalysisService
from school_lab.errors import AnalysisFailure

@pytest.fixture
def example(valid):
    submission = parse_submission(valid)
    ctx = AnalysisContext(Assignment("assignment-01", "from typing import Iterable\n", ("Наличие solve",)))
    return submission, ctx

@pytest.mark.parametrize("analyzer_cls", [LengthAnalyzer, TemplateAnalyzer, DeclarationAnalyzer])
def test_analyzer_contract(example, analyzer_cls):
    submission, ctx = example
    analyzer = analyzer_cls()
    first = analyzer.analyze(submission, ctx)
    second = analyzer.analyze(submission, ctx)
    validate_report(first, submission, ctx)
    assert first.findings == second.findings
    assert first.report_id != second.report_id
    assert first.analyzer_id == analyzer.analyzer_id
    assert first.config_hash == second.config_hash

def test_length_evidence(example):
    submission, ctx = example
    finding = LengthAnalyzer().analyze(submission,ctx).findings[0]
    assert finding.kind == "rubric_feedback" and finding.score is None
    assert len(finding.evidence) == 5
    assert any(e.field == "text" and e.start_line == 3 for e in finding.evidence)

def test_template_exact(example):
    submission, ctx = example
    finding = TemplateAnalyzer().analyze(submission,ctx).findings[0]
    assert finding.kind == "similarity" and finding.evidence[0].start_line == 1
    assert "не нарушение" in finding.explanation
    assert template_ranges("a\nb\na\nb\n", "a\nb\n") == ((1,2),(3,4))

def test_invalid_evidence_rejected(example):
    submission, ctx = example
    good = LengthAnalyzer().analyze(submission,ctx)
    bad_e = replace(good.findings[0].evidence[0], end_line=500)
    bad_f = replace(good.findings[0],evidence=(bad_e,))
    with pytest.raises(AnalysisFailure):
        validate_report(replace(good,findings=(bad_f,)),submission,ctx)

def test_analysis_error_and_registry(valid):
    repo = InMemorySubmissionRepository()
    SubmissionService(repo).accept(valid)
    registry = default_registry()
    registry.register("declaration",DeclarationAnalyzer)
    assert registry.create("declaration").analyzer_id == "declaration"
    with pytest.raises(AnalysisFailure):
        registry.register("length",LengthAnalyzer)
    context = AnalysisContext(Assignment("assignment-01","",()))
    service = AnalysisService(repo,registry)
    assert service.run(valid["submission_id"],"declaration",context).analyzer_id == "declaration"
    class Broken:
        analyzer_id = "broken"
        analyzer_version = "1.0"
        def analyze(self, submission, context):
            return "bad"
    registry.register("broken",Broken)
    with pytest.raises(AnalysisFailure):
        service.run(valid["submission_id"],"broken",context)
    class Crashed:
        analyzer_id = "crashed"
        analyzer_version = "1.0"
        def analyze(self, submission, context):
            raise ZeroDivisionError("oops")
    registry.register("crashed", Crashed)
    with pytest.raises(AnalysisFailure,match="Ошибка анализатора"):
        service.run(valid["submission_id"],"crashed",context)
